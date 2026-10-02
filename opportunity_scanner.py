"""Cripto Radar IA - M3: Agente Buscador de Oportunidades.

Escanea el mercado con CoinGecko y detecta movimientos por reglas simples:
- SUBIDA 24h: +10% o mas en 24h
- MOVIMIENTO 1h: +3% o mas en 1h
- PICO VOLUMEN: volumen/market_cap >= 15%

Solo analiza y reporta. NUNCA ejecuta compra/venta (regla dura W1).
"""
import requests

API = "https://api.coingecko.com/api/v3/coins/markets"
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) CriptoRadar/0.1"}

# Stablecoins: no son oportunidades de trading, se excluyen
STABLECOINS = {
    "usdt", "usdc", "dai", "busd", "tusd", "fdusd", "usde", "usdd",
    "susd", "gusd", "usdp", "usdm", "usdx", "usdr", "usds", "usdl",
    "eurc", "eurt", "xsgd", "usd0", "pyusd", "usdtb", "usd1", "usdg",
}

# Config de reglas (ajustable)
TOP_N = 100              # cuantas monedas escanear
MIN_MARKET_CAP = 50_000_000   # minimo $50M para filtrar basura
SIGNAL_24H = 10.0        # % subida en 24h -> "subida fuerte"
SIGNAL_1H = 3.0          # % subida en 1h -> "movimiento fuerte"
VOLUME_RATIO = 0.15      # volumen/market_cap -> "pico de volumen"


def fetch_market(n=TOP_N):
    params = {
        "vs_currency": "usd",
        "order": "market_cap_desc",
        "per_page": n,
        "page": 1,
        "sparkline": "false",
        "price_change_percentage": "1h,24h,7d",
    }
    r = requests.get(API, params=params, headers=HEADERS, timeout=20)
    r.raise_for_status()
    return r.json()


def is_tradable(c):
    """Filtra stablecoins y monedas sin liquidez suficiente."""
    if c["symbol"].lower() in STABLECOINS:
        return False
    if c.get("market_cap") is None or c["market_cap"] < MIN_MARKET_CAP:
        return False
    if not c.get("total_volume"):
        return False
    return True


def build_signals(c):
    """Devuelve la lista de senales detectadas para una moneda."""
    sigs = []
    p24 = c.get("price_change_percentage_24h") or 0
    p1h = c.get("price_change_percentage_1h_in_currency") or 0
    vol_ratio = c["total_volume"] / c["market_cap"]
    if p24 >= SIGNAL_24H:
        sigs.append(("SUBIDA 24h", f"+{p24:.1f}%"))
    if p1h >= SIGNAL_1H:
        sigs.append(("MOV 1h", f"+{p1h:.1f}%"))
    if vol_ratio >= VOLUME_RATIO:
        sigs.append(("PICO VOL", f"{vol_ratio*100:.0f}% cap"))
    return sigs


def fmt_precio(p):
    """Decimales segun magnitud: las monedas micro no pueden quedar en $0.0000."""
    if p >= 1:
        return f"${p:,.2f}"
    if p >= 0.01:
        return f"${p:,.4f}"
    if p >= 0.0001:
        return f"${p:,.6f}"
    return f"${p:,.10f}".rstrip("0")


def build_report():
    """Devuelve el informe como texto (lo usa radar.py para mandarlo a Telegram)."""
    data = fetch_market()
    lineas = []
    for c in data:
        if not is_tradable(c):
            continue
        sigs = build_signals(c)
        if sigs:
            desc = " | ".join(f"{s} {v}" for s, v in sigs)
            lineas.append(f"\U0001F7E2 {c['symbol'].upper()} ${c['current_price']:,.4f} - {desc}")

    if not lineas:
        return "\U0001F50D BUSCADOR: sin oportunidades (nada supero los umbrales)."

    cabecera = (
        f"\U0001F50D BUSCADOR: {len(lineas)} senal(es) "
        f"(24h>={SIGNAL_24H:.0f}% | 1h>={SIGNAL_1H:.0f}% | vol>={VOLUME_RATIO*100:.0f}% cap)"
    )
    return cabecera + "\n" + "\n".join(lineas)


def main():
    print(build_report())


if __name__ == "__main__":
    main()
