"""Cripto Radar IA - S1: backtesting de senales.

Pregunta: las senales del Buscador, ¿anticipan algo o son ruido?

Como lo responde:
- Baja ~90 dias de historia por hora de CoinGecko (cacheada en data/).
- Reconstruye, hora por hora, la misma "moneda" que ve el scanner en vivo
  y le aplica las funciones REALES de opportunity_scanner.py (no una copia).
- Mide el rendimiento a +4h, +24h y +7d despues de cada senal y lo compara
  contra la linea base: esa misma moneda en una hora cualquiera del periodo.

Dos conteos distintos:
- DISPAROS: cuantas veces salta la regla -> mide el ruido (alertas por pasada).
- EVENTOS: primer disparo despues de 24h sin disparar -> mide si sirve.
  Sin esto, una moneda con volumen alto 3 dias seguidos aporta 72 "aciertos"
  que en realidad son uno solo.

Limites (van escritos en el informe): sesgo de supervivencia (se prueba sobre
el top de HOY) y un solo regimen de mercado (90 dias).

Solo analiza datos publicos. NUNCA ejecuta compra/venta (regla dura W1).
"""
import json
import os
import statistics
import sys
import time
from collections import defaultdict
from datetime import datetime, timezone

import requests

import opportunity_scanner as scanner

HERE = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(HERE, "data")
SALIDA = os.path.join(HERE, "backtest_resultados.md")

DIAS = 90            # 2-90 dias -> CoinGecko devuelve granularidad horaria
UNIVERSO = 30        # monedas a probar (limite de llamadas de la API gratis)
HORIZONTES = (4, 24, 168)
COOLDOWN = 24        # horas sin disparar para que cuente como evento nuevo
PAUSA = 6.5          # segundos entre llamadas (~9 por minuto)
MUESTRA_MIN = 20     # por debajo de esto no se saca conclusion

BARRIDO = {
    "VOLUME_RATIO": ("PICO VOL", [0.15, 0.25, 0.35, 0.50]),
    "SIGNAL_24H": ("SUBIDA 24h", [10.0, 15.0, 20.0]),
    "SIGNAL_1H": ("MOV 1h", [3.0, 4.0, 5.0]),
}

NOMBRES = {4: "+4h", 24: "+24h", 168: "+7d"}
TIPOS = ("SUBIDA 24h", "MOV 1h", "PICO VOL")


# ---------- datos ----------

def pedir(url, params):
    """GET con reintento si CoinGecko limita (429)."""
    for intento in range(5):
        r = requests.get(url, params=params, headers=scanner.HEADERS, timeout=30)
        if r.status_code == 429:
            espera = 60 * (intento + 1)
            print(f"   CoinGecko limito las llamadas, espero {espera}s...")
            time.sleep(espera)
            continue
        r.raise_for_status()
        return r.json()
    raise RuntimeError("CoinGecko sigue limitando despues de 5 intentos")


def cache_json(nombre, fn):
    """Devuelve (json, bajado). Usa data/<nombre> si existe; si no, lo baja con fn() y lo guarda."""
    ruta = os.path.join(CACHE, nombre)
    if os.path.exists(ruta):
        with open(ruta, encoding="utf-8") as f:
            return json.load(f), False
    datos = fn()
    os.makedirs(CACHE, exist_ok=True)
    with open(ruta, "w", encoding="utf-8") as f:
        json.dump(datos, f)
    return datos, True


def universo():
    """Top N operables (sin stablecoins), congelado en cache para que sea reproducible."""
    def bajar():
        data = pedir(scanner.API, {
            "vs_currency": "usd", "order": "market_cap_desc",
            "per_page": UNIVERSO * 2, "page": 1, "sparkline": "false",
        })
        return [[c["id"], c["symbol"].upper()] for c in data if scanner.is_tradable(c)][:UNIVERSO]
    lista, _ = cache_json("universo.json", bajar)
    return lista


def historia(cid):
    url = f"https://api.coingecko.com/api/v3/coins/{cid}/market_chart"
    datos, bajado = cache_json(
        f"{cid}.json",
        lambda: pedir(url, {"vs_currency": "usd", "days": DIAS}),
    )
    if bajado:
        time.sleep(PAUSA)
    return datos


def por_hora(serie):
    """[[ms, valor], ...] -> {hora_entera: valor}."""
    return {int(ms // 3_600_000): v for ms, v in serie}


def fotos(sym, hist):
    """Reconstruye hora por hora el dict que el scanner ve en vivo, mas los rendimientos futuros."""
    P = por_hora(hist["prices"])
    V = por_hora(hist["total_volumes"])
    M = por_hora(hist["market_caps"])
    salida = []
    for h in sorted(P):
        if (h - 1) not in P or (h - 24) not in P or h not in V or h not in M:
            continue
        p = P[h]
        moneda = {
            "symbol": sym,
            "current_price": p,
            "price_change_percentage_24h": (p / P[h - 24] - 1) * 100,
            "price_change_percentage_1h_in_currency": (p / P[h - 1] - 1) * 100,
            "total_volume": V[h],
            "market_cap": M[h],
        }
        futuro = {k: ((P[h + k] / p - 1) * 100 if (h + k) in P else None) for k in HORIZONTES}
        salida.append((h, moneda, futuro))
    return salida


# ---------- evaluacion ----------

def evaluar(datos):
    """Aplica las reglas actuales del scanner a toda la historia."""
    base = {}
    tipos = defaultdict(lambda: {"disparos": 0, "eventos": []})
    alertas_por_hora = defaultdict(int)
    horas = set()

    for sym, snaps in datos.items():
        operables = [(h, c, f) for h, c, f in snaps if scanner.is_tradable(c)]
        base[sym] = {}
        for k in HORIZONTES:
            valores = [f[k] for _, _, f in operables if f[k] is not None]
            if valores:
                base[sym][k] = statistics.mean(valores)

        ultimo = {}
        for h, c, fut in operables:
            horas.add(h)
            sigs = scanner.build_signals(c)
            if sigs:
                alertas_por_hora[h] += 1
            for tipo, _ in sigs:
                d = tipos[tipo]
                d["disparos"] += 1
                previo = ultimo.get(tipo)
                ultimo[tipo] = h
                if previo is None or h - previo > COOLDOWN:
                    d["eventos"].append((sym, fut))

    n_horas = len(horas) or 1
    resumen = {}
    for tipo, d in tipos.items():
        fila = {"disparos_por_pasada": d["disparos"] / n_horas, "eventos": len(d["eventos"])}
        for k in HORIZONTES:
            pares = [(f[k], f[k] - base[s][k]) for s, f in d["eventos"]
                     if f[k] is not None and k in base[s]]
            if pares:
                ret = [r for r, _ in pares]
                exc = [e for _, e in pares]
                fila[k] = {
                    "n": len(pares),
                    "acierto": 100 * sum(r > 0 for r in ret) / len(ret),
                    "mediana": statistics.median(ret),
                    "exceso": statistics.median(exc),
                    "gana_base": 100 * sum(e > 0 for e in exc) / len(exc),
                }
        resumen[tipo] = fila

    linea_base = {}
    for k in HORIZONTES:
        todos = [f[k] for snaps in datos.values() for _, c, f in snaps
                 if f[k] is not None and scanner.is_tradable(c)]
        if todos:
            linea_base[k] = {
                "acierto": 100 * sum(r > 0 for r in todos) / len(todos),
                "mediana": statistics.median(todos),
            }

    total_alertas = sum(alertas_por_hora.values()) / n_horas
    return resumen, linea_base, total_alertas, n_horas


def veredicto(fila):
    d = fila.get(24)
    if not d or d["n"] < MUESTRA_MIN:
        return "muestra chica, sin conclusión"
    if d["exceso"] > 0 and d["gana_base"] >= 55:
        return "ventaja"
    if d["exceso"] < 0 and d["gana_base"] <= 45:
        return "peor que el azar"
    return "ruido"


# ---------- informe ----------

def pct(x):
    return f"{x:+.2f}%"


def informe(datos, desde, hasta):
    L = []
    L.append("# Backtest de señales — Cripto Radar IA\n")
    L.append(
        f"Generado: {datetime.now(timezone.utc):%Y-%m-%d %H:%M} UTC · "
        f"Período: {desde:%Y-%m-%d} → {hasta:%Y-%m-%d} · "
        f"Universo: {len(datos)} monedas (top por cap, sin stablecoins) · Datos por hora\n"
    )

    res, lb, total, n_horas = evaluar(datos)

    L.append("## 1. Con los umbrales actuales\n")
    L.append(
        f"Umbrales: SUBIDA 24h ≥ {scanner.SIGNAL_24H:.0f}% · MOV 1h ≥ {scanner.SIGNAL_1H:.0f}% · "
        f"PICO VOL ≥ {scanner.VOLUME_RATIO * 100:.0f}% del cap\n"
    )
    L.append(
        f"**Monedas con alerta por pasada (promedio): {total:.1f}** "
        f"sobre {len(datos)} monedas y {n_horas} horas.\n"
    )

    L.append("| Señal | Disparos por pasada | Eventos | Acierto 24h | Mediana 24h | Exceso vs base 24h | Le gana a la base | Veredicto |")
    L.append("|---|---|---|---|---|---|---|---|")
    for tipo in TIPOS:
        f = res.get(tipo)
        if not f:
            L.append(f"| {tipo} | 0 | 0 | — | — | — | — | nunca disparó |")
            continue
        d = f.get(24)
        if d:
            L.append(
                f"| {tipo} | {f['disparos_por_pasada']:.2f} | {f['eventos']} | {d['acierto']:.0f}% | "
                f"{pct(d['mediana'])} | {pct(d['exceso'])} | {d['gana_base']:.0f}% | {veredicto(f)} |"
            )
        else:
            L.append(f"| {tipo} | {f['disparos_por_pasada']:.2f} | {f['eventos']} | — | — | — | — | sin datos a 24h |")
    if 24 in lb:
        L.append(
            f"| *Línea base (hora cualquiera)* | — | — | {lb[24]['acierto']:.0f}% | "
            f"{pct(lb[24]['mediana'])} | 0 | 50% | referencia |"
        )

    L.append("\n### Todos los horizontes\n")
    L.append("| Señal | Horizonte | n | Acierto | Mediana | Exceso vs base | Le gana a la base |")
    L.append("|---|---|---|---|---|---|---|")
    for tipo in TIPOS:
        for k in HORIZONTES:
            d = res.get(tipo, {}).get(k)
            if d:
                L.append(
                    f"| {tipo} | {NOMBRES[k]} | {d['n']} | {d['acierto']:.0f}% | "
                    f"{pct(d['mediana'])} | {pct(d['exceso'])} | {d['gana_base']:.0f}% |"
                )
    for k in HORIZONTES:
        if k in lb:
            L.append(f"| *Línea base* | {NOMBRES[k]} | — | {lb[k]['acierto']:.0f}% | {pct(lb[k]['mediana'])} | 0 | 50% |")

    L.append("\n## 2. Barrido de umbrales\n")
    L.append(
        "Se cambia **un umbral a la vez**; los otros quedan como están. "
        "Mide qué pasa con el ruido (disparos) y con la ventaja (exceso a 24h).\n"
    )
    L.append("| Regla | Umbral | Disparos por pasada | Eventos | Exceso vs base 24h | Le gana a la base 24h | Veredicto |")
    L.append("|---|---|---|---|---|---|---|")
    for const, (tipo, valores) in BARRIDO.items():
        original = getattr(scanner, const)
        try:
            for v in valores:
                setattr(scanner, const, v)
                r, _, _, _ = evaluar(datos)
                f = r.get(tipo)
                etiqueta = f"{v * 100:.0f}% cap" if const == "VOLUME_RATIO" else f"{v:.0f}%"
                actual = " (actual)" if v == original else ""
                if not f or 24 not in f:
                    L.append(f"| {tipo} | {etiqueta}{actual} | 0 | 0 | — | — | nunca disparó |")
                else:
                    d = f[24]
                    L.append(
                        f"| {tipo} | {etiqueta}{actual} | {f['disparos_por_pasada']:.2f} | {f['eventos']} | "
                        f"{pct(d['exceso'])} | {d['gana_base']:.0f}% | {veredicto(f)} |"
                    )
        finally:
            setattr(scanner, const, original)

    L.append("\n## 3. Cómo leer esto\n")
    L.append("- **Disparos por pasada**: cuántas alertas de ese tipo te llegan cada vez que corre el radar. Es el ruido.")
    L.append("- **Eventos**: primer disparo después de 24h sin disparar. Es la muestra real con la que se mide si la señal sirve.")
    L.append("- **Exceso vs base**: rendimiento después de la señal **menos** el rendimiento promedio de esa misma moneda en una hora cualquiera. Positivo = la señal anticipa algo.")
    L.append("- **Le gana a la base**: % de eventos con exceso positivo. 50% es una moneda al aire.")
    L.append(
        f"- **Veredicto** (a 24h): *ventaja* si el exceso es positivo y le gana a la base ≥55% de las veces; "
        f"*peor que el azar* si es negativo y le gana ≤45%; *muestra chica* con menos de {MUESTRA_MIN} eventos; *ruido* en el resto."
    )

    L.append("\n## 4. Límites — leer antes de decidir\n")
    L.append("- 🪞 **Sesgo de supervivencia.** El universo es el top de *hoy*. Las monedas que se fundieron en el período no están, y eso infla los resultados.")
    L.append(f"- 📉 **Un solo régimen de mercado.** {DIAS} días no dicen nada sobre un mercado distinto al de este período.")
    L.append("- ⏱️ **Datos por hora.** El radar en vivo corre cada 30 min; acá se evalúa una vez por hora.")
    L.append("- 🧮 **Muchas pruebas a la vez.** Con 3 reglas × 3 horizontes × varios umbrales, alguna va a salir \"buena\" por casualidad. Un resultado aislado no alcanza: tiene que ser consistente entre horizontes.")
    L.append("- ⛔ **No es una estrategia de trading.** No hay comisiones, deslizamiento ni gestión de riesgo. Solo responde si la señal anticipa movimiento.")
    return "\n".join(L) + "\n"


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

    monedas = universo()
    print(f"Universo: {len(monedas)} monedas -> {', '.join(s for _, s in monedas)}\n")

    datos = {}
    for i, (cid, sym) in enumerate(monedas, 1):
        print(f"[{i:>2}/{len(monedas)}] {sym:<6} ", end="", flush=True)
        try:
            snaps = fotos(sym, historia(cid))
            datos[sym] = snaps
            print(f"{len(snaps)} horas")
        except Exception as e:
            print(f"SALTEADA ({type(e).__name__}: {e})")

    if not datos:
        print("No se pudo bajar ninguna moneda. Nada que evaluar.")
        return

    horas = [h for s in datos.values() for h, _, _ in s]
    desde = datetime.fromtimestamp(min(horas) * 3600, timezone.utc)
    hasta = datetime.fromtimestamp(max(horas) * 3600, timezone.utc)

    texto = informe(datos, desde, hasta)
    with open(SALIDA, "w", encoding="utf-8", newline="\n") as f:
        f.write(texto)
    print("\n" + texto)
    print(f"Informe guardado en {SALIDA}")


if __name__ == "__main__":
    main()
