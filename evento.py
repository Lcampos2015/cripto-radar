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
VENTANA_RECIENTE_MIN = 60   # el cron se atrasa: un cruce de la ultima hora todavia cuenta como nuevo
VELAS_24H = 96              # velas de 15 minutos en 24 horas


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


def decidir(cambios, umbral, ultimo_aviso, ahora_ms):
    """Funcion pura. Devuelve +1 / -1 si hay que avisar de una subida / caida, o None.

    cambios: [(ms, pct)] ordenados; el ultimo es el momento actual.
    ultimo_aviso: {"ms": ..., "signo": ...} de esta moneda, o None.
    """
    if not cambios:
        return None
    _, actual = cambios[-1]
    if abs(actual) < umbral:
        return None
    signo = 1 if actual > 0 else -1
    desde = ahora_ms - COOLDOWN_H * 3600_000
    hasta = ahora_ms - VENTANA_RECIENTE_MIN * 60_000
    if any(desde <= ms < hasta and pct * signo >= umbral for ms, pct in cambios[:-1]):
        return None            # ya venia superado de antes: no es un evento nuevo
    if (ultimo_aviso and ultimo_aviso.get("signo") == signo
            and ahora_ms - ultimo_aviso["ms"] < COOLDOWN_H * 3600_000):
        return None            # ya se aviso de este mismo movimiento
    return signo


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
    eventos = []
    for moneda, (simbolo, _) in briefing_datos.MONEDAS.items():
        tec = briefing_datos.tecnico(simbolo)
        umbral = K_ATR * tec["atr_pct"]
        cambios = cambios_24h(velas_15m(simbolo))
        _, actual = cambios[-1]
        signo = decidir(cambios, umbral, estado.get(moneda), ahora_ms)
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
