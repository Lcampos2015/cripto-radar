"""Calibracion de V3-7: cuantos briefings extra por mes daria cada umbral.

Evento = el cambio de las ultimas 24h (en cualquier direccion) CRUZA k x ATR%
(ATR(14) diario del dia anterior, en % del precio). Para no repetir: solo cuenta
si en las 12h previas ese mismo umbral no se habia superado en la misma
direccion. Es la misma logica que usa evento.py, aplicada a 1 año de velas
horarias de Binance.
"""
import sys
import time
from collections import defaultdict
from datetime import datetime, timezone

import requests

from backtest_swing import atr

KLINES = "https://data-api.binance.vision/api/v3/klines"
KS = (1.5, 2.0, 2.5, 3.0)
DIAS = 365


def bajar(simbolo, intervalo, desde_ms):
    velas, inicio = [], desde_ms
    while True:
        r = requests.get(KLINES, params={"symbol": simbolo, "interval": intervalo, "startTime": inicio, "limit": 1000}, timeout=30)
        r.raise_for_status()
        lote = r.json()
        if not lote:
            break
        velas += lote
        inicio = lote[-1][0] + 1
        if len(lote) < 1000:
            break
        time.sleep(0.3)
    return [v for v in velas if v[6] < time.time() * 1000]


def eventos(horas, atr_por_dia, k):
    """horas: [(ms, cierre)]. Devuelve [(ms, cambio_24h_pct)] de cada evento."""
    idx = {ms: i for i, (ms, _) in enumerate(horas)}
    cambios = [None] * len(horas)
    for i in range(24, len(horas)):
        if horas[i][0] - horas[i - 24][0] == 24 * 3600_000:
            cambios[i] = (horas[i][1] / horas[i - 24][1] - 1) * 100
    out = []
    for i, (ms, _) in enumerate(horas):
        c = cambios[i]
        dia = datetime.fromtimestamp(ms / 1000, timezone.utc).strftime("%Y-%m-%d")
        a = atr_por_dia.get(dia)
        if c is None or a is None:
            continue
        umbral = k * a
        if abs(c) < umbral:
            continue
        signo = 1 if c > 0 else -1
        previos = [cambios[j] for j in range(max(0, i - 12), i)]
        if any(p is not None and p * signo >= umbral for p in previos):
            continue
        out.append((ms, c))
    return out


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    desde = int((time.time() - (DIAS + 40) * 86400) * 1000)
    resultados = defaultdict(dict)
    for sim in ("BTCUSDT", "ETHUSDT"):
        d = bajar(sim, "1d", desde)
        h, l, c = ([float(v[k]) for v in d] for k in (2, 3, 4))
        a = atr(h, l, c)
        # ATR% del dia ANTERIOR (lo que se conoce durante el dia)
        atr_por_dia = {}
        for i in range(1, len(d)):
            if a[i - 1] is not None:
                dia = datetime.fromtimestamp(d[i][0] / 1000, timezone.utc).strftime("%Y-%m-%d")
                atr_por_dia[dia] = a[i - 1] / c[i - 1] * 100
        horas = [(v[0], float(v[4])) for v in bajar(sim, "1h", desde + 40 * 86400_000)]
        meses = len(horas) / 24 / 30.44
        for k in KS:
            ev = eventos(horas, atr_por_dia, k)
            resultados[k][sim[:3]] = (len(ev), meses, ev)

    print(f"Último año de velas horarias de Binance. ATR% típico hoy: BTC ~2,8%, ETH ~3,5%.\n")
    print(f"{'Umbral':<10}{'BTC/mes':>9}{'ETH/mes':>9}{'TOTAL/mes':>11}   ejemplos (más recientes)")
    for k in KS:
        b, e = resultados[k]["BTC"], resultados[k]["ETH"]
        tot = (b[0] + e[0]) / b[1]
        ej = sorted([("BTC", ms, c) for ms, c in b[2]] + [("ETH", ms, c) for ms, c in e[2]], key=lambda x: -x[1])[:3]
        ejs = ", ".join(f"{m} {c:+.1f}% el {datetime.fromtimestamp(ms/1000, timezone.utc):%d/%m}" for m, ms, c in ej)
        print(f"{k:.1f}×ATR   {b[0]/b[1]:>8.1f}{e[0]/e[1]:>9.1f}{tot:>11.1f}   {ejs}")


if __name__ == "__main__":
    main()
