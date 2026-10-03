"""Prueba que fuentes publicas de velas diarias (OHLC) responden desde donde se corre.

Se corre en la PC y en GitHub Actions (workflow probe.yml) para comparar.
Solo endpoints publicos de datos de mercado: sin claves, solo lectura (W1).
"""
import os
import sys
from datetime import datetime, timezone

import requests

H = {"User-Agent": "CriptoRadar/0.1"}

FUENTES = {
    "binance (api.binance.com)": (
        "https://api.binance.com/api/v3/klines",
        {"symbol": "BTCUSDT", "interval": "1d", "limit": 1000},
    ),
    "binance (data-api.binance.vision)": (
        "https://data-api.binance.vision/api/v3/klines",
        {"symbol": "BTCUSDT", "interval": "1d", "limit": 1000},
    ),
    "coinbase": (
        "https://api.exchange.coinbase.com/products/BTC-USD/candles",
        {"granularity": 86400},
    ),
    "kraken": (
        "https://api.kraken.com/0/public/OHLC",
        {"pair": "XBTUSD", "interval": 1440},
    ),
}


def velas(nombre, data):
    """Devuelve (cantidad, fecha_mas_vieja, fecha_mas_nueva) segun el formato de cada fuente."""
    if nombre.startswith("binance"):
        ts = [v[0] / 1000 for v in data]
    elif nombre == "coinbase":
        ts = [v[0] for v in data]
    else:  # kraken
        serie = next(v for k, v in data["result"].items() if k != "last")
        ts = [v[0] for v in serie]
    f = lambda t: datetime.fromtimestamp(t, timezone.utc).strftime("%Y-%m-%d")
    return len(ts), f(min(ts)), f(max(ts))


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    en_actions = os.environ.get("GITHUB_ACTIONS") == "true"
    for nombre, (url, params) in FUENTES.items():
        try:
            r = requests.get(url, params=params, headers=H, timeout=20)
            if r.status_code != 200:
                linea = f"FALLA  {nombre:<34} HTTP {r.status_code}: {r.text[:90]!r}"
            else:
                n, desde, hasta = velas(nombre, r.json())
                linea = f"OK     {nombre:<34} {n:>4} velas diarias  {desde} -> {hasta}"
        except Exception as e:
            linea = f"FALLA  {nombre:<34} {type(e).__name__}: {str(e)[:90]}"
        print(linea)
        if en_actions:
            # Anotacion del run: se lee por la API publica sin iniciar sesion
            print(f"::notice title=probe::{linea}")


if __name__ == "__main__":
    main()
