"""Cripto Radar IA - F1b: protocolo anti-casualidad.

Implementa EXACTAMENTE lo que esta en PREREGISTRO.md (commit 4707a82, 2026-10-03
08:29, anterior a este codigo). No agregar estrategias ni cambiar parametros o
umbrales sin un pre-registro nuevo.

Uso:
    python backtest_f1b.py              -> solo exploracion (2020-2023)
    python backtest_f1b.py --sellado    -> exploracion + caja fuerte (2024-hoy),
                                           solo para las que sobreviven. UNA vez.

Datos: velas diarias de Binance (data-api.binance.vision) y Coin Metrics
community API. Todo publico, sin claves. Solo simula: NUNCA opera (W1).
"""
import argparse
import json
import os
import random
import statistics
import sys
from datetime import date, datetime, timedelta, timezone

import requests

import backtest_swing as bs

HERE = os.path.dirname(os.path.abspath(__file__))
SALIDA = os.path.join(HERE, "backtest_f1b_resultados.md")

EXPLORACION = ("2020-01-01", "2023-12-31")
SELLADO_DESDE = "2024-01-01"
N_ESTRATEGIAS = 6
ALFA = 0.05 / N_ESTRATEGIAS          # 0,0083
N_AZAR = 1000
SEMILLA = 20261003                   # fija, para que el test al azar sea reproducible
MIN_OPS_EXP = 30
MIN_OPS_SELLADO = 15
ANIOS_EXP = ("2020", "2021", "2022", "2023")

CM_URL = "https://community-api.coinmetrics.io/v4/timeseries/asset-metrics"
CM_METRICAS = ("CapMVRVCur", "FlowInExNtv", "FlowOutExNtv")
ACTIVO = {"BTCUSDT": "btc", "ETHUSDT": "eth"}
SIMBOLOS = bs.SIMBOLOS


# ---------- datos ----------

def bajar_coinmetrics():
    """MVRV y flujos de exchanges diarios desde 2018-06 (para tener ventanas de hasta 456 dias en 2020)."""
    ruta = os.path.join(bs.CACHE, "coinmetrics.json")
    if os.path.exists(ruta):
        with open(ruta, encoding="utf-8") as f:
            return json.load(f)
    url, params, filas = CM_URL, {
        "assets": "btc,eth", "metrics": ",".join(CM_METRICAS), "frequency": "1d",
        "start_time": "2018-06-01", "page_size": 10000,
    }, []
    while url:
        r = requests.get(url, params=params, timeout=60)
        r.raise_for_status()
        j = r.json()
        filas += j.get("data", [])
        url, params = j.get("next_page_url"), None
    datos = {"btc": {}, "eth": {}}
    for fila in filas:
        try:
            datos[fila["asset"]][fila["time"][:10]] = {m: float(fila[m]) for m in CM_METRICAS}
        except (KeyError, TypeError, ValueError):
            continue   # dia con alguna metrica faltante: se ignora
    os.makedirs(bs.CACHE, exist_ok=True)
    with open(ruta, "w", encoding="utf-8") as f:
        json.dump(datos, f)
    return datos


def preparar():
    cm = bajar_coinmetrics()
    series = {}
    for sim in SIMBOLOS:
        s = bs.preparar(sim)
        s["cm"] = cm[ACTIVO[sim]]
        s["cache"] = {}
        series[sim] = s
    fechas = sorted(set.intersection(*(set(s["fecha"]) for s in series.values())))
    return series, fechas


# ---------- indicadores (cacheados por serie y parametros) ----------

def cache(s, clave, calcular):
    if clave not in s["cache"]:
        s["cache"][clave] = calcular()
    return s["cache"][clave]


def EMA(s, n):
    return cache(s, ("ema", n), lambda: bs.ema(s["c"], n))


def MACD(s, rapida, lenta, senal):
    def calcular():
        a, b = EMA(s, rapida), EMA(s, lenta)
        m = [x - y if x is not None and y is not None else None for x, y in zip(a, b)]
        inicio = next(i for i, v in enumerate(m) if v is not None)
        return m, [None] * inicio + bs.ema(m[inicio:], senal)
    return cache(s, ("macd", rapida, lenta, senal), calcular)


def BANDA_INF(s, n, k):
    def calcular():
        c, out = s["c"], [None] * len(s["c"])
        for i in range(n - 1, len(c)):
            w = c[i - n + 1:i + 1]
            m = sum(w) / n
            out[i] = m - k * (sum((x - m) ** 2 for x in w) / n) ** 0.5
        return out
    return cache(s, ("boll", n, k), calcular)


def dias_previos(fecha, n):
    d = date.fromisoformat(fecha)
    return [(d - timedelta(days=k)).isoformat() for k in range(n, 0, -1)]


def FLUJO_Z(s, W):
    """z-score del flujo neto del dia ANTERIOR (desfase de 1 dia), contra los W dias previos a ese."""
    def calcular():
        cm, out = s["cm"], [None] * len(s["fecha"])
        neto = lambda f: cm[f]["FlowInExNtv"] - cm[f]["FlowOutExNtv"] if f in cm else None
        for i in range(1, len(s["fecha"])):
            ayer = s["fecha"][i - 1]
            x = neto(ayer)
            ventana = [neto(f) for f in dias_previos(ayer, W)]
            if x is None or None in ventana:
                continue
            m = sum(ventana) / W
            sd = (sum((v - m) ** 2 for v in ventana) / W) ** 0.5
            if sd > 0:
                out[i] = (x - m) / sd
        return out
    return cache(s, ("flujoz", W), calcular)


def MVRV_BAJO(s, M):
    """MVRV del dia ANTERIOR (desfase de 1 dia) por debajo de su media de los M dias previos."""
    def calcular():
        cm, out = s["cm"], [None] * len(s["fecha"])
        mv = lambda f: cm[f]["CapMVRVCur"] if f in cm else None
        for i in range(1, len(s["fecha"])):
            ayer = s["fecha"][i - 1]
            x = mv(ayer)
            ventana = [mv(f) for f in dias_previos(ayer, M)]
            if x is None or None in ventana:
                continue
            out[i] = x < sum(ventana) / M
        return out
    return cache(s, ("mvrv", M), calcular)


# ---------- las 6 estrategias pre-registradas ----------

def retroceso(r, l):
    def senal(s, i):
        a, b, c200 = EMA(s, r), EMA(s, l), EMA(s, 200)
        if None in (a[i], b[i], c200[i]):
            return False
        return a[i] > b[i] > c200[i] and s["l"][i] <= a[i] and s["c"][i] > a[i]
    return senal


def macd(rapida, lenta, sen):
    def senal(s, i):
        m, sig = MACD(s, rapida, lenta, sen)
        if None in (m[i], m[i - 1], sig[i], sig[i - 1]):
            return False
        return m[i - 1] <= sig[i - 1] and m[i] > sig[i]
    return senal


def bollinger(n, k):
    def senal(s, i):
        inf, c = BANDA_INF(s, n, k), s["c"]
        if None in (inf[i], inf[i - 1]):
            return False
        return c[i - 1] < inf[i - 1] and c[i] > inf[i]
    return senal


def compresion(N):
    def senal(s, i):
        if i < N:
            return False
        rangos = [s["h"][j] - s["l"][j] for j in range(i - N, i)]   # los N dias que terminan ayer
        return rangos[-1] == min(rangos) and s["c"][i] > s["h"][i - 1]
    return senal


def flujo(W, umbral):
    def senal(s, i):
        z = FLUJO_Z(s, W)[i]
        return z is not None and z <= umbral
    return senal


def barato(M, g):
    def senal(s, i):
        bajo, e, c = MVRV_BAJO(s, M)[i], EMA(s, g), s["c"]
        if not bajo or None in (e[i], e[i - 1]):
            return False
        return c[i - 1] <= e[i - 1] and c[i] > e[i]
    return senal


# (nombre, fabrica, parametros, vecino -25%, vecino +25%) -- tal cual PREREGISTRO.md
ESTRATEGIAS = [
    ("🪃 Retroceso en tendencia", retroceso, (20, 50), (15, 38), (25, 63)),
    ("〰️ Cruce MACD", macd, (12, 26, 9), (9, 20, 7), (15, 33, 11)),
    ("🎈 Rebote Bollinger", bollinger, (20, 2.0), (15, 1.5), (25, 2.5)),
    ("🗜️ Compresión NR", compresion, (7,), (5,), (9,)),
    ("🏦 Salida masiva de exchanges", flujo, (30, -2.0), (22, -1.5), (38, -2.5)),
    ("📊 Barato + gatillo", barato, (365, 20), (274, 15), (456, 25)),
]


# ---------- simulacion (reglas F0) ----------

def filtro_btc(series, fecha):
    b = series["BTCUSDT"]
    i = b["idx"][fecha]
    return b["ema200"][i] is not None and b["c"][i] > b["ema200"][i]


def simular(series, fechas, desde, hasta, elegir):
    """Entradas solo entre desde y hasta; la operacion abierta al final se cierra con datos posteriores (max 5 dias)."""
    cash, pos = bs.CAPITAL_INICIAL, None
    ops, curva, oportunidades = [], [], 0
    mes_actual, equity_mes, frenado = None, None, False
    d0 = next(d for d, f in enumerate(fechas) if f >= desde)

    for d in range(d0, len(fechas)):
        fecha = fechas[d]
        if pos:
            s = series[pos["sim"]]
            i = s["idx"][fecha]
            o, h, l, c = s["o"][i], s["h"][i], s["l"][i], s["c"][i]
            pos["dias"] += 1
            salida = None
            if l <= pos["stop"]:
                salida = min(o, pos["stop"])
            elif h >= pos["objetivo"]:
                salida = max(o, pos["objetivo"])
            elif pos["dias"] >= bs.DIAS_MAX:
                salida = c
            if salida is not None:
                bruto = pos["qty"] * salida * (1 - bs.COMISION)
                cash += bruto
                pnl = bruto - pos["costo"]
                ops.append({"sim": pos["sim"][:3], "entrada": pos["fecha"], "R": pnl / pos["riesgo"], "pnl": pnl})
                pos = None
        if fecha > hasta:
            if pos:
                continue
            break

        equity = cash
        if pos:
            s = series[pos["sim"]]
            equity += pos["qty"] * s["c"][s["idx"][fecha]]
        curva.append((fecha, equity))
        if fecha[:7] != mes_actual:
            mes_actual, equity_mes, frenado = fecha[:7], equity, False
        if not frenado and equity <= equity_mes * (1 - bs.FRENO_MES):
            frenado = True

        if pos or frenado or d + 1 >= len(fechas) or not filtro_btc(series, fecha):
            continue
        oportunidades += 1
        sim = elegir(fecha)
        if not sim:
            continue
        s = series[sim]
        i = s["idx"][fecha]
        j = s["idx"][fechas[d + 1]]
        entrada = s["o"][j]
        stop = entrada - bs.STOP_ATR * s["atr"][i]
        riesgo = bs.RIESGO * equity
        qty = riesgo / (entrada - stop)
        if qty * entrada * (1 + bs.COMISION) > cash:
            qty = cash / (entrada * (1 + bs.COMISION))
        costo = qty * entrada * (1 + bs.COMISION)
        cash -= costo
        pos = {"sim": sim, "qty": qty, "stop": stop, "objetivo": entrada + bs.OBJETIVO_ATR * s["atr"][i],
               "dias": 0, "fecha": fechas[d + 1], "costo": costo, "riesgo": riesgo}

    return ops, curva, oportunidades


def por_estrategia(series, senal):
    def elegir(fecha):
        for sim in SIMBOLOS:
            s = series[sim]
            i = s["idx"][fecha]
            if s["atr"][i] is not None and senal(s, i):
                return sim
        return None
    return elegir


def al_azar(series, q, rng):
    def elegir(fecha):
        if rng.random() >= q:
            return None
        sim = rng.choice(SIMBOLOS)
        return sim if series[sim]["atr"][series[sim]["idx"][fecha]] is not None else None
    return elegir


# ---------- metricas ----------

def esperanza(ops):
    return statistics.mean(o["R"] for o in ops) if ops else None


def resumir(ops, curva):
    valores = [e for _, e in curva]
    n_anios = bs.anios(curva)
    g = bs.cagr(bs.CAPITAL_INICIAL, valores[-1], n_anios)
    dd = bs.max_dd(valores)
    por_anio, por_moneda = {}, {}
    for o in ops:
        por_anio[o["entrada"][:4]] = por_anio.get(o["entrada"][:4], 0) + o["R"]
        por_moneda.setdefault(o["sim"], []).append(o)
    return {
        "n": len(ops), "esp": esperanza(ops), "cagr": g, "dd": dd, "calmar": g / dd if dd else 0,
        "por_anio": por_anio,
        "por_moneda": {m: (len(v), esperanza(v)) for m, v in por_moneda.items()},
        "final": valores[-1],
    }


def mantener(serie, fechas, desde, hasta):
    ev = [f for f in fechas if desde <= f <= hasta]
    base = serie["o"][serie["idx"][ev[0]]]
    vals = [serie["c"][serie["idx"][f]] / base for f in ev]
    g = bs.cagr(1, vals[-1], bs.anios([(ev[0], 0), (ev[-1], 0)]))
    dd = bs.max_dd(vals)
    return {"cagr": g, "dd": dd, "calmar": g / dd if dd else 0}


def test_azar(series, fechas, desde, hasta, n_ops, oportunidades, esp_real, semilla):
    """p = (k+1)/(N+1), k = simulaciones al azar con esperanza >= la real."""
    if not n_ops or esp_real is None:
        return 1.0, []
    q = n_ops / oportunidades
    rng = random.Random(semilla)
    esps = []
    for _ in range(N_AZAR):
        ops, _, _ = simular(series, fechas, desde, hasta, al_azar(series, q, rng))
        esps.append(esperanza(ops))
    k = sum(1 for e in esps if e is not None and e >= esp_real)
    return (k + 1) / (N_AZAR + 1), esps


# ---------- corrida ----------

def correr(series, fechas, desde, hasta, nombre, fabrica, params, semilla):
    ops, curva, oport = simular(series, fechas, desde, hasta, por_estrategia(series, fabrica(*params)))
    r = resumir(ops, curva)
    r["p"], esps = test_azar(series, fechas, desde, hasta, r["n"], oport, r["esp"], semilla)
    validas = [e for e in esps if e is not None]
    r["azar_mediana"] = statistics.median(validas) if validas else None
    return r


def f(x, nd=2):
    return "—" if x is None else f"{x:+.{nd}f}"


def ok(b):
    return "✅" if b else "❌"


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    ap = argparse.ArgumentParser()
    ap.add_argument("--sellado", action="store_true", help="abrir la caja fuerte (2024-hoy). Una sola vez.")
    args = ap.parse_args()

    series, fechas = preparar()
    desde, hasta = EXPLORACION
    vara = max(mantener(series[s], fechas, desde, hasta)["calmar"] for s in SIMBOLOS)
    holds = {s[:3]: mantener(series[s], fechas, desde, hasta) for s in SIMBOLOS}

    filas = []
    for k_est, (nombre, fabrica, base, menos, mas) in enumerate(ESTRATEGIAS):
        print(f"Exploración: {nombre} ...", flush=True)
        r = correr(series, fechas, desde, hasta, nombre, fabrica, base, SEMILLA + k_est)
        vec = []
        for p in (menos, mas):
            ops, _, _ = simular(series, fechas, desde, hasta, por_estrategia(series, fabrica(*p)))
            vec.append((len(ops), esperanza(ops)))
        anios_pos = sum(r["por_anio"].get(a, 0) > 0 for a in ANIOS_EXP)
        monedas_ok = all(m in r["por_moneda"] and (r["por_moneda"][m][1] or 0) > 0 for m in ("BTC", "ETH"))
        c = [
            r["esp"] is not None and r["esp"] > 0,
            r["n"] >= MIN_OPS_EXP,
            anios_pos >= 3,
            monedas_ok,
            all(e is not None and e > 0 for _, e in vec),
            r["p"] < ALFA,
            r["calmar"] > vara,
        ]
        filas.append({"nombre": nombre, "fabrica": fabrica, "base": base, "menos": menos, "mas": mas,
                      "r": r, "vec": vec, "anios_pos": anios_pos, "c": c, "pasa": all(c), "k": k_est})

    L = ["# F1b — Protocolo anti-casualidad: resultados\n"]
    L.append(f"Generado: {datetime.now(timezone.utc):%Y-%m-%d %H:%M} UTC · Pre-registro: `PREREGISTRO.md` (commit 4707a82) · "
             f"Exploración {desde} → {hasta} · Test al azar: {N_AZAR} simulaciones, semilla {SEMILLA} · "
             f"Vara contra el azar p < {ALFA:.4f}\n")
    L.append("## Línea base en exploración (mantener sin tocar)\n")
    L.append("| | Anual | Caída máx. | Anual ÷ caída |")
    L.append("|---|---|---|---|")
    for m, h in holds.items():
        L.append(f"| Mantener {m} | {h['cagr']*100:+.1f}% | {h['dd']*100:.1f}% | {h['calmar']:.2f} |")

    L.append("\n## Exploración 2020–2023: las 7 condiciones\n")
    L.append("| Estrategia | Ops | Esperanza | 1 Esp>0 | 2 ≥30 ops | 3 Años + | 4 BTC y ETH | 5 Vecinos | 6 Azar (p) | 7 Anual÷caída | **Sobrevive** |")
    L.append("|---|---|---|---|---|---|---|---|---|---|---|")
    for x in filas:
        r, c = x["r"], x["c"]
        pm = r["por_moneda"]
        monedas = " / ".join(f"{m} {f(pm[m][1])}" if m in pm else f"{m} —" for m in ("BTC", "ETH"))
        vecs = " / ".join(f(e) for _, e in x["vec"])
        L.append(f"| {x['nombre']} | {r['n']} | {f(r['esp'])} R | {ok(c[0])} | {ok(c[1])} | {ok(c[2])} {x['anios_pos']}/4 | "
                 f"{ok(c[3])} {monedas} | {ok(c[4])} {vecs} | {ok(c[5])} {r['p']:.3f} | {ok(c[6])} {r['calmar']:.2f} vs {vara:.2f} | "
                 f"**{ok(x['pasa'])}** |")

    L.append("\n### Detalle por año (suma de R, por año de entrada)\n")
    L.append("| Estrategia | " + " | ".join(ANIOS_EXP) + " | Azar: esperanza mediana |")
    L.append("|---|" + "---|" * (len(ANIOS_EXP) + 1))
    for x in filas:
        r = x["r"]
        L.append(f"| {x['nombre']} | " + " | ".join(f(r['por_anio'].get(a), 1) if a in r["por_anio"] else "—" for a in ANIOS_EXP)
                 + f" | {f(r['azar_mediana'])} R |")

    sobrevivientes = [x for x in filas if x["pasa"]]
    L.append("\n## Caja fuerte (2024 → hoy)\n")
    if not sobrevivientes:
        L.append("🔒 **Ninguna estrategia sobrevivió la exploración, así que la caja fuerte NO se abrió.** "
                 "Los datos 2024-hoy siguen limpios para un pre-registro futuro.")
    elif not args.sellado:
        L.append(f"Sobreviven {len(sobrevivientes)}: {', '.join(x['nombre'] for x in sobrevivientes)}. "
                 "La caja fuerte sigue cerrada: correr con `--sellado` para abrirla, una sola vez.")
    else:
        alfa_s = 0.05 / len(sobrevivientes)
        hoy = fechas[-1]
        L.append(f"Corrida única: {SELLADO_DESDE} → {hoy}. Vara contra el azar: p < {alfa_s:.4f}.\n")
        L.append("| Estrategia | Ops | Esperanza | 1 Esp>0 | 2 ≥15 ops | 3 Azar (p) | **Pasa a F2/F3** |")
        L.append("|---|---|---|---|---|---|---|")
        for x in sobrevivientes:
            print(f"Caja fuerte: {x['nombre']} ...", flush=True)
            r = correr(series, fechas, SELLADO_DESDE, hoy, x["nombre"], x["fabrica"], x["base"], SEMILLA + 100 + x["k"])
            c = [r["esp"] is not None and r["esp"] > 0, r["n"] >= MIN_OPS_SELLADO, r["p"] < alfa_s]
            L.append(f"| {x['nombre']} | {r['n']} | {f(r['esp'])} R | {ok(c[0])} | {ok(c[1])} | {ok(c[2])} {r['p']:.3f} | **{ok(all(c))}** |")

    L.append("\n## Notas\n")
    L.append("- **Esperanza (R):** ganancia promedio por cada $1 arriesgado, neta de comisiones.")
    L.append("- **Azar (p):** proporción de simulaciones con entradas aleatorias (mismas salidas, tamaño, filtro y freno) que igualaron o superaron a la estrategia. Chico = la señal aporta.")
    L.append("- **Vecinos:** esperanza con todos los parámetros ×0,75 / ×1,25.")
    L.append("- Una operación abierta el último día de un período se cierra con hasta 5 días de datos posteriores.")
    L.append("- Fundamentales con 1 día de desfase. Solo simulación: nada opera (W1).")

    texto = "\n".join(L) + "\n"
    with open(SALIDA, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(texto)
    print("\n" + texto)


if __name__ == "__main__":
    main()
