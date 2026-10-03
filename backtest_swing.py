"""Cripto Radar IA - F1: backtest de estrategias swing.

Prueba 3 estrategias clasicas de swing trading (y cada una con filtro de
contexto) sobre velas diarias de BTC y ETH desde 2020, aplicando las reglas
personales de F0 tal cual. El criterio para "pasar" se fijo ANTES de correrlo.

Datos: API publica de mercado de Binance (data-api.binance.vision), sin clave
y de solo lectura. Es el endpoint que responde desde GitHub Actions;
api.binance.com devuelve HTTP 451 desde EE.UU. (probado 2026-10-03).

Solo simula. NUNCA ejecuta compra/venta (regla dura W1).
"""
import json
import os
import statistics
import sys
import time
from collections import defaultdict
from datetime import datetime, timezone

import requests

HERE = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(HERE, "data")
SALIDA = os.path.join(HERE, "backtest_swing_resultados.md")

KLINES = "https://data-api.binance.vision/api/v3/klines"
SIMBOLOS = ("BTCUSDT", "ETHUSDT")   # prioridad si las dos dan senal el mismo dia
DESDE_DATOS = "2019-05-01"          # calentamiento para la media de 200 dias
DESDE_EVAL = "2020-01-01"

# --- Reglas personales (F0, 2026-10-03) ---
CAPITAL_INICIAL = 100.0
RIESGO = 0.01           # 1% del capital por operacion
STOP_ATR = 1.5          # stop-loss a 1,5 x ATR(14) bajo la entrada
OBJETIVO_ATR = 3.0      # objetivo a 3 x ATR(14): gana el doble de lo que arriesga
DIAS_MAX = 5            # al 5to dia se cierra igual
COMISION = 0.001        # Binance spot, por lado
FRENO_MES = 0.10        # -10% en el mes -> no hay entradas nuevas hasta el mes siguiente

# --- Criterio para pasar (fijado antes de ver resultados) ---
MIN_OPERACIONES = 30


# ---------- datos ----------

def ms(fecha):
    return int(datetime.strptime(fecha, "%Y-%m-%d").replace(tzinfo=timezone.utc).timestamp() * 1000)


def bajar_velas(simbolo):
    """Velas diarias cerradas desde DESDE_DATOS. Cacheadas en data/ (borrar para refrescar)."""
    ruta = os.path.join(CACHE, f"klines_{simbolo}.json")
    if os.path.exists(ruta):
        with open(ruta, encoding="utf-8") as f:
            return json.load(f)
    velas, inicio, ahora = [], ms(DESDE_DATOS), int(time.time() * 1000)
    while True:
        r = requests.get(KLINES, params={"symbol": simbolo, "interval": "1d",
                                         "startTime": inicio, "limit": 1000}, timeout=30)
        r.raise_for_status()
        lote = r.json()
        if not lote:
            break
        velas += lote
        inicio = lote[-1][0] + 1
        if len(lote) < 1000:
            break
        time.sleep(0.5)
    velas = [v for v in velas if v[6] < ahora]   # descarta la vela de hoy, que no cerro
    os.makedirs(CACHE, exist_ok=True)
    with open(ruta, "w", encoding="utf-8") as f:
        json.dump(velas, f)
    return velas


# ---------- indicadores ----------

def ema(xs, n):
    out = [None] * len(xs)
    if len(xs) < n:
        return out
    k = 2 / (n + 1)
    prev = sum(xs[:n]) / n
    out[n - 1] = prev
    for i in range(n, len(xs)):
        prev = xs[i] * k + prev * (1 - k)
        out[i] = prev
    return out


def atr(h, l, c, n=14):
    """ATR de Wilder."""
    tr = [None] + [max(h[i] - l[i], abs(h[i] - c[i - 1]), abs(l[i] - c[i - 1])) for i in range(1, len(c))]
    out = [None] * len(c)
    if len(c) <= n:
        return out
    prev = sum(tr[1:n + 1]) / n
    out[n] = prev
    for i in range(n + 1, len(c)):
        prev = (prev * (n - 1) + tr[i]) / n
        out[i] = prev
    return out


def rsi(c, n=14):
    """RSI de Wilder."""
    out = [None] * len(c)
    if len(c) <= n:
        return out
    sube = [max(c[i] - c[i - 1], 0) for i in range(1, len(c))]
    baja = [max(c[i - 1] - c[i], 0) for i in range(1, len(c))]
    ps, pb = sum(sube[:n]) / n, sum(baja[:n]) / n
    valor = lambda s, b: 100.0 if b == 0 else 100 - 100 / (1 + s / b)
    out[n] = valor(ps, pb)
    for i in range(n + 1, len(c)):
        ps = (ps * (n - 1) + sube[i - 1]) / n
        pb = (pb * (n - 1) + baja[i - 1]) / n
        out[i] = valor(ps, pb)
    return out


def preparar(simbolo):
    velas = bajar_velas(simbolo)
    fecha = [datetime.fromtimestamp(v[0] / 1000, timezone.utc).strftime("%Y-%m-%d") for v in velas]
    o, h, l, c = ([float(v[k]) for v in velas] for k in (1, 2, 3, 4))
    return {
        "fecha": fecha, "idx": {f: i for i, f in enumerate(fecha)},
        "o": o, "h": h, "l": l, "c": c,
        "ema20": ema(c, 20), "ema50": ema(c, 50), "ema200": ema(c, 200),
        "atr": atr(h, l, c), "rsi": rsi(c),
    }


# ---------- estrategias (parametros de manual, sin ajustar) ----------

def tendencia(s, i):
    """El cierre cruza arriba de la EMA20, con la EMA20 sobre la EMA50."""
    e20, e50, c = s["ema20"], s["ema50"], s["c"]
    if None in (e20[i], e20[i - 1], e50[i]):
        return False
    return c[i] > e20[i] and c[i - 1] <= e20[i - 1] and e20[i] > e50[i]


def ruptura(s, i):
    """El cierre supera el maximo de los 20 dias anteriores."""
    return i >= 20 and s["c"][i] > max(s["h"][i - 20:i])


def rebote(s, i):
    """El RSI(14) sale de sobreventa (cruza 30 hacia arriba) con el precio sobre la EMA200."""
    r, e = s["rsi"], s["ema200"]
    if None in (r[i], r[i - 1], e[i]):
        return False
    return r[i - 1] < 30 <= r[i] and s["c"][i] > e[i]


ESTRATEGIAS = {"Tendencia": tendencia, "Ruptura": ruptura, "Rebote": rebote}


# ---------- simulacion ----------

def simular(series, fechas, senal, con_filtro):
    btc = series["BTCUSDT"]
    cash, pos = CAPITAL_INICIAL, None
    ops, curva, dias_invertido, frenos = [], [], 0, 0
    mes_actual, equity_mes, frenado = None, None, False

    for d, fecha in enumerate(fechas):
        # 1) gestionar la posicion abierta durante este dia
        if pos:
            s = series[pos["sim"]]
            i = s["idx"][fecha]
            o, h, l, c = s["o"][i], s["h"][i], s["l"][i], s["c"][i]
            pos["dias"] += 1
            dias_invertido += 1
            salida = None
            if l <= pos["stop"]:                       # si toca los dos el mismo dia, se asume el stop
                salida = (min(o, pos["stop"]), "stop")
            elif h >= pos["objetivo"]:
                salida = (max(o, pos["objetivo"]), "objetivo")
            elif pos["dias"] >= DIAS_MAX:
                salida = (c, "dia 5")
            if salida:
                precio, motivo = salida
                bruto = pos["qty"] * precio
                cash += bruto * (1 - COMISION)
                pnl = bruto * (1 - COMISION) - pos["costo"]
                ops.append({"sim": pos["sim"][:3], "entrada": pos["fecha"], "salida": fecha,
                            "motivo": motivo, "pnl": pnl, "R": pnl / pos["riesgo"]})
                pos = None

        if fecha < DESDE_EVAL:
            continue

        equity = cash
        if pos:
            s = series[pos["sim"]]
            equity += pos["qty"] * s["c"][s["idx"][fecha]]
        curva.append((fecha, equity))

        # freno mensual
        if fecha[:7] != mes_actual:
            mes_actual, equity_mes, frenado = fecha[:7], equity, False
        if not frenado and equity <= equity_mes * (1 - FRENO_MES):
            frenado, frenos = True, frenos + 1

        # 2) buscar entrada al cierre de hoy; se compra en la apertura de manana
        if pos or frenado or d + 1 >= len(fechas):
            continue
        if con_filtro:
            bi = btc["idx"][fecha]
            if btc["ema200"][bi] is None or btc["c"][bi] <= btc["ema200"][bi]:
                continue
        for sim in SIMBOLOS:
            s = series[sim]
            i = s["idx"][fecha]
            if s["atr"][i] is None or not senal(s, i):
                continue
            j = s["idx"][fechas[d + 1]]
            entrada = s["o"][j]
            stop = entrada - STOP_ATR * s["atr"][i]
            objetivo = entrada + OBJETIVO_ATR * s["atr"][i]
            riesgo = RIESGO * equity
            qty = riesgo / (entrada - stop)
            if qty * entrada * (1 + COMISION) > cash:     # sin apalancamiento
                qty = cash / (entrada * (1 + COMISION))
            costo = qty * entrada * (1 + COMISION)
            cash -= costo
            pos = {"sim": sim, "qty": qty, "stop": stop, "objetivo": objetivo, "dias": 0,
                   "fecha": fechas[d + 1], "costo": costo, "riesgo": riesgo}
            break

    return ops, curva, dias_invertido, frenos


# ---------- metricas ----------

def max_dd(valores):
    pico, dd = valores[0], 0.0
    for v in valores:
        pico = max(pico, v)
        dd = max(dd, (pico - v) / pico)
    return dd


def anios(curva):
    d0 = datetime.strptime(curva[0][0], "%Y-%m-%d")
    d1 = datetime.strptime(curva[-1][0], "%Y-%m-%d")
    return (d1 - d0).days / 365.25


def cagr(inicial, final, n_anios):
    return (final / inicial) ** (1 / n_anios) - 1 if final > 0 else -1.0


def mantener(s, fechas):
    """Comprar en la apertura del primer dia evaluado y no tocar."""
    evals = [f for f in fechas if f >= DESDE_EVAL]
    base = s["o"][s["idx"][evals[0]]]
    valores = [s["c"][s["idx"][f]] / base for f in evals]
    n = anios([(evals[0], 0), (evals[-1], 0)])
    g = cagr(1, valores[-1], n)
    dd = max_dd(valores)
    return {"retorno": valores[-1] - 1, "cagr": g, "dd": dd, "calmar": g / dd if dd else 0}


def resumir(ops, curva, dias_inv):
    valores = [e for _, e in curva]
    n = anios(curva)
    g = cagr(CAPITAL_INICIAL, valores[-1], n)
    dd = max_dd(valores)
    por_anio = defaultdict(float)
    for op in ops:
        por_anio[op["salida"][:4]] += op["R"]
    return {
        "n": len(ops),
        "ganadoras": 100 * sum(op["pnl"] > 0 for op in ops) / len(ops) if ops else 0,
        "esperanza": statistics.mean(op["R"] for op in ops) if ops else 0,
        "retorno": valores[-1] / CAPITAL_INICIAL - 1,
        "cagr": g, "dd": dd, "calmar": g / dd if dd else 0,
        "exposicion": 100 * dias_inv / len(curva),
        "por_anio": dict(sorted(por_anio.items())),
        "motivos": {m: sum(op["motivo"] == m for op in ops) for m in ("objetivo", "stop", "dia 5")},
        "final": valores[-1],
    }


# ---------- informe ----------

def pct(x, signo=True):
    return f"{x * 100:+.1f}%" if signo else f"{x * 100:.1f}%"


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

    series = {sim: preparar(sim) for sim in SIMBOLOS}
    fechas = sorted(set.intersection(*(set(s["fecha"]) for s in series.values())))
    evals = [f for f in fechas if f >= DESDE_EVAL]

    base = {sim[:3]: mantener(series[sim], fechas) for sim in SIMBOLOS}
    vara = max(b["calmar"] for b in base.values())

    resultados = []
    for nombre, fn in ESTRATEGIAS.items():
        for filtro in (False, True):
            ops, curva, dias_inv, frenos = simular(series, fechas, fn, filtro)
            r = resumir(ops, curva, dias_inv)
            r["nombre"] = nombre + (" + filtro BTC" if filtro else "")
            r["frenos"] = frenos
            anios_con_ops = len(r["por_anio"])
            anios_pos = sum(v > 0 for v in r["por_anio"].values())
            r["anios_txt"] = f"{anios_pos}/{anios_con_ops}"
            r["c"] = [
                r["esperanza"] > 0,
                r["n"] >= MIN_OPERACIONES,
                anios_con_ops > 0 and anios_pos > anios_con_ops / 2,
                r["calmar"] > vara,
            ]
            r["pasa"] = all(r["c"])
            resultados.append(r)

    ok = lambda b: "✅" if b else "❌"
    L = ["# Backtest swing — Cripto Radar IA (F1)\n"]
    L.append(f"Generado: {datetime.now(timezone.utc):%Y-%m-%d %H:%M} UTC · Velas diarias Binance "
             f"(data-api.binance.vision) · BTC y ETH · {evals[0]} → {evals[-1]} ({anios([(evals[0],0),(evals[-1],0)]):.1f} años)\n")
    L.append(f"Reglas F0: capital inicial ${CAPITAL_INICIAL:.0f} · riesgo {RIESGO*100:.0f}% por operación · "
             f"stop {STOP_ATR}×ATR · objetivo {OBJETIVO_ATR}×ATR · máx. {DIAS_MAX} días · 1 operación a la vez · "
             f"freno −{FRENO_MES*100:.0f}% mensual · comisión {COMISION*100:.1f}% por lado · sin apalancamiento\n")

    L.append("## Línea base: comprar y no tocar\n")
    L.append("| | Retorno total | Anual (CAGR) | Caída máxima | Anual ÷ caída |")
    L.append("|---|---|---|---|---|")
    for k, b in base.items():
        L.append(f"| Mantener {k} | {pct(b['retorno'])} | {pct(b['cagr'])} | {pct(b['dd'], False)} | {b['calmar']:.2f} |")

    L.append("\n## Criterio para pasar (fijado antes de correr)\n")
    L.append("1. **Esperanza > 0**: en promedio gana algo por cada $1 que arriesga, ya descontadas las comisiones.")
    L.append(f"2. **≥ {MIN_OPERACIONES} operaciones**.")
    L.append("3. **Positiva en la mayoría de los años** con operaciones.")
    L.append(f"4. **Anual ÷ caída mejor que mantener BTC y que mantener ETH** (la vara: {vara:.2f}).\n")

    L.append("## Resultados\n")
    L.append("| Estrategia | Ops | Ganadoras | Esperanza (R) | Años + | Anual | Caída máx. | Anual ÷ caída | Expuesto | 1 | 2 | 3 | 4 | **Pasa** |")
    L.append("|---|---|---|---|---|---|---|---|---|---|---|---|---|---|")
    for r in resultados:
        c1, c2, c3, c4 = (ok(x) for x in r["c"])
        L.append(f"| {r['nombre']} | {r['n']} | {r['ganadoras']:.0f}% | {r['esperanza']:+.2f} | {r['anios_txt']} | "
                 f"{pct(r['cagr'])} | {pct(r['dd'], False)} | {r['calmar']:.2f} | {r['exposicion']:.0f}% | "
                 f"{c1} | {c2} | {c3} | {c4} | **{ok(r['pasa'])}** |")

    L.append("\n### Resultado por año (suma de R)\n")
    todos_anios = sorted({a for r in resultados for a in r["por_anio"]})
    L.append("| Estrategia | " + " | ".join(todos_anios) + " |")
    L.append("|---|" + "---|" * len(todos_anios))
    for r in resultados:
        L.append(f"| {r['nombre']} | " + " | ".join(
            f"{r['por_anio'][a]:+.1f}" if a in r["por_anio"] else "—" for a in todos_anios) + " |")

    L.append("\n### Cómo terminaron las operaciones\n")
    L.append("| Estrategia | Objetivo | Stop | Día 5 | Frenos mensuales | Capital final |")
    L.append("|---|---|---|---|---|---|")
    for r in resultados:
        m = r["motivos"]
        L.append(f"| {r['nombre']} | {m['objetivo']} | {m['stop']} | {m['dia 5']} | {r['frenos']} | ${r['final']:.2f} |")

    L.append("\n## Cómo leer esto\n")
    L.append("- **R** = lo que arriesgás por operación (1% del capital). Esperanza +0,10 R = en promedio ganás 10 centavos por cada $1 arriesgado.")
    L.append("- **Anual ÷ caída**: cuánto rinde por año en relación al peor bajón que tuviste que aguantar. Es la forma justa de comparar contra mantener, porque la estrategia está invertida solo una parte del tiempo (columna *Expuesto*).")
    L.append("- **Años +**: años con resultado positivo sobre años con operaciones.")

    L.append("\n## Límites — leer antes de decidir\n")
    L.append("- 🧮 **6 variantes a la vez.** Alguna puede pasar por suerte. La que pase tiene que ser consistente año a año, y después confirmarse en paper trading (F3).")
    L.append("- 📉 **Deslizamiento no modelado.** Se asume que entrás exactamente en la apertura y salís exactamente en el stop u objetivo (salvo gaps). En la vida real es un poco peor.")
    L.append("- ⚖️ **Si el mismo día se tocan stop y objetivo, se asume el stop** (supuesto conservador: con velas diarias no se sabe cuál fue primero).")
    L.append("- 🕰️ **El pasado no garantiza nada.** Esto mide si la regla tuvo ventaja en 2020-2026, no si la va a tener.")
    L.append("- ⛔ **Es simulación.** Ninguna línea de este código opera (W1).")

    pasan = [r["nombre"] for r in resultados if r["pasa"]]
    L.append("\n## Veredicto\n")
    L.append(f"**Pasan las cuatro condiciones:** {', '.join(pasan)}." if pasan
             else "**Ninguna estrategia pasa las cuatro condiciones.**")

    texto = "\n".join(L) + "\n"
    with open(SALIDA, "w", encoding="utf-8", newline="\n") as f:
        f.write(texto)
    print(texto)


if __name__ == "__main__":
    main()
