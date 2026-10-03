"""Cripto Radar IA - V3-1: recolector de datos duros para el briefing.

Arma el JSON del dia con lo que el LLM va a poder usar. Los numeros salen de
aca y NUNCA del LLM (el verificador de V3-3 compara contra este JSON).

Fuentes publicas, sin clave, que responden desde GitHub Actions:
- Binance (data-api.binance.vision): velas diarias -> precio e indicadores
- Coin Metrics community: MVRV y flujos de exchanges (llegan con ~1 dia de atraso)
- alternative.me: indice de miedo/codicia

Si una fuente falla, se anota en "faltantes" y el resto sigue.
Solo lee datos. NUNCA ejecuta compra/venta (regla dura W1).
"""
import json
import statistics
import sys
import time
from datetime import date, datetime, timedelta, timezone

import requests

from backtest_swing import atr, ema, rsi

KLINES = "https://data-api.binance.vision/api/v3/klines"
CM_URL = "https://community-api.coinmetrics.io/v4/timeseries/asset-metrics"
FNG_URL = "https://api.alternative.me/fng/"
MONEDAS = {"BTC": ("BTCUSDT", "btc"), "ETH": ("ETHUSDT", "eth")}
H = {"User-Agent": "CriptoRadar/0.1"}


def r(x, nd=2):
    return None if x is None else round(x, nd)


def pct(a, b):
    return None if a is None or not b else round((a / b - 1) * 100, 2)


# ---------- fuentes ----------

def velas(simbolo):
    """Ultimas 1000 velas diarias CERRADAS. Con 500, la EMA200 arrastraba ~5% de error del arranque
    (difería $256 de TradingView el 2026-10-03); con 1000 coincide al centavo."""
    resp = requests.get(KLINES, params={"symbol": simbolo, "interval": "1d", "limit": 1000}, headers=H, timeout=30)
    resp.raise_for_status()
    ahora = int(time.time() * 1000)
    return [v for v in resp.json() if v[6] < ahora]


def tecnico(simbolo):
    v = velas(simbolo)
    c = [float(x[4]) for x in v]
    h = [float(x[2]) for x in v]
    l = [float(x[3]) for x in v]
    vol = [float(x[7]) for x in v]          # volumen en USDT
    e20, e50, e200 = ema(c, 20)[-1], ema(c, 50)[-1], ema(c, 200)[-1]
    a = atr(h, l, c)[-1]
    cierre = c[-1]
    prom_vol20 = statistics.mean(vol[-21:-1])
    return {
        "fecha_vela": datetime.fromtimestamp(v[-1][0] / 1000, timezone.utc).strftime("%Y-%m-%d"),
        "cierre": r(cierre),
        "cambio_1d_pct": pct(cierre, c[-2]),
        "cambio_7d_pct": pct(cierre, c[-8]),
        "cambio_30d_pct": pct(cierre, c[-31]),
        "ema20": r(e20), "ema50": r(e50), "ema200": r(e200),
        "sobre_ema20": cierre > e20, "sobre_ema50": cierre > e50, "sobre_ema200": cierre > e200,
        "dist_ema200_pct": pct(cierre, e200),
        "rsi14": r(rsi(c)[-1], 1),
        "atr14": r(a), "atr_pct": r(a / cierre * 100),
        "maximo_20d": r(max(h[-20:])), "minimo_20d": r(min(l[-20:])),
        "volumen_usd_1d": r(vol[-1], 0),
        "volumen_vs_prom_20d": r(vol[-1] / prom_vol20, 2),
    }


def onchain():
    """MVRV y flujo neto de exchanges, BTC y ETH. Ultimos ~400 dias para la media de 365 y el z-score de 30."""
    desde = (date.today() - timedelta(days=400)).isoformat()
    params = {"assets": "btc,eth", "metrics": "CapMVRVCur,FlowInExNtv,FlowOutExNtv",
              "frequency": "1d", "start_time": desde, "page_size": 10000}
    resp = requests.get(CM_URL, params=params, headers=H, timeout=60)
    resp.raise_for_status()
    filas = {"btc": [], "eth": []}
    for f in resp.json().get("data", []):
        try:
            filas[f["asset"]].append((f["time"][:10], float(f["CapMVRVCur"]),
                                      float(f["FlowInExNtv"]) - float(f["FlowOutExNtv"])))
        except (KeyError, TypeError, ValueError):
            continue
    out = {}
    for activo, datos in filas.items():
        datos.sort()
        fecha, mvrv, neto = datos[-1]
        mvrvs = [m for _, m, _ in datos[-366:-1]]
        netos = [n for _, _, n in datos[-31:-1]]
        sd = statistics.pstdev(netos)
        media_mvrv = statistics.mean(mvrvs)
        z = (neto - statistics.mean(netos)) / sd if sd else None
        out[activo] = {
            "fecha_onchain": fecha,
            "mvrv": r(mvrv),
            "mvrv_media_365d": r(media_mvrv),
            "flujo_neto_exchanges": r(neto, 1),      # en unidades de la moneda; negativo = sale de exchanges
            "flujo_neto_z30": r(z, 2) if z is not None else None,
            # Lecturas en palabras, hechas por el CODIGO y no por el LLM: el 2026-10-03 gpt-5.4-mini
            # escribio "salida neta" para un flujo positivo (entraban monedas). Un signo no se interpreta mal aca.
            "mvrv_lectura": ("por encima de su media del año (relativamente caro)" if mvrv > media_mvrv
                             else "por debajo de su media del año (relativamente barato)"),
            "flujo_lectura": ("entran a los exchanges más monedas de las que salen (posible presión de venta)" if neto > 0
                              else "salen de los exchanges más monedas de las que entran (menos oferta para vender)"),
            "flujo_inusual": None if z is None else abs(z) >= 2,
        }
    return out


def miedo_codicia():
    resp = requests.get(FNG_URL, params={"limit": 1}, headers=H, timeout=20)
    resp.raise_for_status()
    d = resp.json()["data"][0]
    return {
        "valor": int(d["value"]),
        "clasificacion": d["value_classification"],
        "fecha": datetime.fromtimestamp(int(d["timestamp"]), timezone.utc).strftime("%Y-%m-%d"),
    }


# ---------- armado ----------

def recolectar():
    datos = {
        "generado_utc": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M"),
        "monedas": {},
        "faltantes": [],
    }
    for nombre, (simbolo, _) in MONEDAS.items():
        try:
            datos["monedas"][nombre] = tecnico(simbolo)
        except Exception as e:
            datos["monedas"][nombre] = {}
            datos["faltantes"].append(f"tecnico {nombre}: {type(e).__name__}")

    try:
        oc = onchain()
        for nombre, (_, activo) in MONEDAS.items():
            datos["monedas"][nombre].update(oc.get(activo, {}))
    except Exception as e:
        datos["faltantes"].append(f"onchain: {type(e).__name__}")

    try:
        datos["miedo_codicia"] = miedo_codicia()
    except Exception as e:
        datos["miedo_codicia"] = None
        datos["faltantes"].append(f"miedo_codicia: {type(e).__name__}")

    btc = datos["monedas"].get("BTC", {})
    datos["regimen"] = {
        "btc_sobre_ema200": btc.get("sobre_ema200"),
        "nota": "Filtro de régimen del backtest F1b: en 2020-2023, estar fuera cuando BTC estaba bajo su EMA200 evitó casi todo 2022.",
    }
    return datos


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    print(json.dumps(recolectar(), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
