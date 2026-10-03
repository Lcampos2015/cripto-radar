"""Cripto Radar IA - V3-7: briefing EXTRA por movimiento fuerte en BTC o ETH.

Corre cada 30 min dentro del workflow del radar. Hay evento cuando el cambio
de las ultimas 24h (subida o caida) supera K_ATR veces la volatilidad normal
de la moneda (ATR diario en %). Con 2,5x salen ~1 por mes (calibrar_evento.py,
ultimo año), umbral elegido por Lucho el 2026-10-03.

Para no repetir el aviso (GitHub Actions no tiene memoria entre corridas):
- si en las 12h previas ya estaba por encima del umbral, no es un evento nuevo;
- el ultimo aviso por moneda queda en estado_eventos.json, que el workflow
  commitea SOLO cuando se avisa.

Uso:
    python evento.py                  -> deteccion normal
    python evento.py --forzar BTC     -> PRUEBA: arma y manda un briefing de evento
                                         con el movimiento actual, sin guardar estado
Solo informa: NUNCA ejecuta compra/venta (regla dura W1).
"""
import argparse
import json
import os
import sys
from datetime import datetime, timezone

import requests

import briefing
import briefing_datos
import notify

HERE = os.path.dirname(os.path.abspath(__file__))
ESTADO = os.path.join(HERE, "estado_eventos.json")
KLINES = briefing_datos.KLINES

K_ATR = 2.5                 # decision de Lucho, 2026-10-03
COOLDOWN_H = 12
VELAS_24H = 96              # velas de 15 minutos en 24 horas
# GitHub NO corre el cron cada 30 min: el 2026-10-03 lo corria cada 4-5 horas. Por eso la
# ventana "nueva" va desde la corrida anterior REAL (consultada a la API), no desde hace 30 min.


def velas_15m(simbolo):
    """Ultimas 200 velas de 15 min; la ultima es la vela en curso (precio actual)."""
    r = requests.get(KLINES, params={"symbol": simbolo, "interval": "15m", "limit": 200},
                     headers=briefing_datos.H, timeout=30)
    r.raise_for_status()
    return [(v[0], float(v[4])) for v in r.json()]


def cambios_24h(velas):
    """[(ms, cambio % contra el precio de 24h antes)]."""
    out = []
    for i in range(VELAS_24H, len(velas)):
        if velas[i][0] - velas[i - VELAS_24H][0] == VELAS_24H * 900_000:
            out.append((velas[i][0], (velas[i][1] / velas[i - VELAS_24H][1] - 1) * 100))
    return out


def decidir(cambios, umbral, ultimo_aviso, ahora_ms, corrida_anterior_ms=None):
    """Funcion pura. Devuelve +1 / -1 si hay que avisar de una subida / caida, o None.

    cambios: [(ms, pct)] ordenados; el ultimo es el momento actual.
    ultimo_aviso: {"ms": ..., "signo": ...} de esta moneda, o None.
    corrida_anterior_ms: cuando corrio el radar la vez anterior. Un cruce posterior a eso
        es nuevo (la corrida anterior no pudo verlo). Si no se sabe, solo se evita repetir
        con el estado guardado.
    """
    if not cambios:
        return None
    _, actual = cambios[-1]
    if abs(actual) < umbral:
        return None
    signo = 1 if actual > 0 else -1
    desde = ahora_ms - COOLDOWN_H * 3600_000
    hasta = corrida_anterior_ms if corrida_anterior_ms is not None else desde
    if any(desde <= ms < hasta and pct * signo >= umbral for ms, pct in cambios[:-1]):
        return None            # ya estaba superado cuando corrio la vez anterior: no es nuevo
    if (ultimo_aviso and ultimo_aviso.get("signo") == signo
            and ahora_ms - ultimo_aviso["ms"] < COOLDOWN_H * 3600_000):
        return None            # ya se aviso de este mismo movimiento
    return signo


def corrida_anterior_ms():
    """Inicio de la ultima corrida TERMINADA de radar.yml (la actual esta en curso).
    Solo en GitHub Actions; si la API falla, None (queda solo el estado para no repetir)."""
    if os.environ.get("GITHUB_ACTIONS") != "true":
        return None
    try:
        url = f"{os.environ['GITHUB_API_URL']}/repos/{os.environ['GITHUB_REPOSITORY']}/actions/workflows/radar.yml/runs"
        r = requests.get(url, params={"status": "completed", "per_page": 1}, timeout=20, headers={
            "Authorization": f"Bearer {os.environ['GITHUB_TOKEN']}", "Accept": "application/vnd.github+json"})
        r.raise_for_status()
        runs = r.json()["workflow_runs"]
        if not runs:
            return None
        return int(datetime.strptime(runs[0]["run_started_at"], "%Y-%m-%dT%H:%M:%SZ")
                   .replace(tzinfo=timezone.utc).timestamp() * 1000)
    except Exception as e:
        print(f"No se pudo consultar la corrida anterior ({type(e).__name__}); solo se usa el estado guardado.")
        return None


def leer_estado():
    if os.path.exists(ESTADO):
        with open(ESTADO, encoding="utf-8") as f:
            return json.load(f)
    return {}


def guardar_estado(estado):
    with open(ESTADO, "w", encoding="utf-8", newline="\n") as f:
        json.dump(estado, f, ensure_ascii=False, indent=2)
        f.write("\n")


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    ap = argparse.ArgumentParser()
    ap.add_argument("--forzar", choices=list(briefing_datos.MONEDAS), help="prueba: manda un briefing de evento sin guardar estado")
    args = ap.parse_args()

    ahora_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
    estado = leer_estado()
    anterior = corrida_anterior_ms()
    if anterior:
        print(f"Corrida anterior: hace {(ahora_ms - anterior) / 3600_000:.1f} h")
    eventos = []
    for moneda, (simbolo, _) in briefing_datos.MONEDAS.items():
        tec = briefing_datos.tecnico(simbolo)
        umbral = K_ATR * tec["atr_pct"]
        cambios = cambios_24h(velas_15m(simbolo))
        _, actual = cambios[-1]
        signo = decidir(cambios, umbral, estado.get(moneda), ahora_ms, anterior)
        print(f"{moneda}: cambio 24h {actual:+.2f}% | umbral ±{umbral:.2f}% ({K_ATR}×ATR {tec['atr_pct']}%) | evento: {bool(signo)}")
        if signo or args.forzar == moneda:
            eventos.append({
                "moneda": moneda,
                "cambio_24h_pct": round(actual, 2),
                "precio_actual": round(velas_15m(simbolo)[-1][1], 2),
                "umbral_pct": round(umbral, 2),
                "veces_atr": K_ATR,
                "hora_utc": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M"),
            })
            if signo and not args.forzar:
                estado[moneda] = {"ms": ahora_ms, "signo": signo}

    if not eventos:
        print("Sin eventos. No se envía nada.")
        return

    datos = briefing_datos.recolectar()
    datos["evento"] = eventos
    titulo = "⚡ BRIEFING POR EVENTO · " + " · ".join(f"{e['moneda']} {e['cambio_24h_pct']:+.1f}% en 24h" for e in eventos)
    if args.forzar:
        titulo = "[PRUEBA] " + titulo
    mensaje, info = briefing.armar(datos, titulo)
    print(mensaje)
    print("\n--- log ---\n", info)
    print("Enviado:", notify.send_telegram(mensaje))
    if not args.forzar:
        guardar_estado(estado)
    if os.environ.get("GITHUB_ACTIONS") == "true":
        print(f"::notice title=evento::{[e['moneda'] for e in eventos]} {info}")


if __name__ == "__main__":
    main()
