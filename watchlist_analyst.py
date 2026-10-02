"""Cripto Radar IA - M4: Agente Analista 24/7.

Monitorea una watchlist fija y genera un informe con precios, tendencia,
volatilidad y liquidez. Solo analiza y reporta. NUNCA ejecuta (regla dura W1).
"""
import requests

API = "https://api.coingecko.com/api/v3/coins/markets"
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) CriptoRadar/0.1"}

# Watchlist: id de CoinGecko -> simbolo (editable)
WATCHLIST = {
    "bitcoin": "BTC",
    "ethereum": "ETH",
    "worldcoin-wld": "WLD",
    "near": "NEAR",
    "ripple": "XRP",
}


def fetch_watchlist(ids):
    params = {
        "vs_currency": "usd",
        "ids": ",".join(ids),
        "order": "market_cap_desc",
        "per_page": 100,
        "page": 1,
        "sparkline": "false",
        "price_change_percentage": "1h,24h,7d",
    }
    r = requests.get(API, params=params, headers=HEADERS, timeout=20)
    r.raise_for_status()
    return r.json()


def trend(p24, p7d):
    """Clasifica la tendencia segun cambios de 24h y 7d."""
    if p24 >= 3 and p7d >= 0:
        return "alcista"
    if p24 <= -3 and p7d <= 0:
        return "bajista"
    return "lateral"


def volatility(p24):
    m = abs(p24)
    if m >= 10:
        return "muy alta"
    if m >= 5:
        return "alta"
    if m >= 2:
        return "media"
    return "baja"


def build_report():
    """Devuelve el informe como texto (lo usa radar.py para mandarlo a Telegram)."""
    data = fetch_watchlist(list(WATCHLIST.keys()))
    by_id = {c["id"]: c for c in data}

    lineas = ["\U0001F4CA ANALISTA 24/7 - WATCHLIST"]
    filas = []
    for cid, sym in WATCHLIST.items():
        c = by_id.get(cid)
        if not c:
            lineas.append(f"⚠ {sym}: sin datos")
            continue
        p = c["current_price"]
        p24 = c.get("price_change_percentage_24h") or 0
        p7d = c.get("price_change_percentage_7d_in_currency") or 0
        mc = c.get("market_cap") or 0
        vol = c.get("total_volume") or 0
        vol_ratio = vol / mc if mc else 0
        filas.append((sym, p, p24, p7d))
        lineas.append(
            f"\n{sym} ${p:,.2f} | {trend(p24, p7d)} | volat. {volatility(p24)}"
            f"\n   24h {p24:+.2f}% | 7d {p7d:+.2f}% | cap ${mc/1e9:,.2f}B | vol/cap {vol_ratio*100:.0f}%"
        )

    if filas:
        mejor = max(filas, key=lambda r: r[2])
        peor = min(filas, key=lambda r: r[2])
        lineas.append(f"\nMejor 24h: {mejor[0]} {mejor[2]:+.2f}% | Peor 24h: {peor[0]} {peor[2]:+.2f}%")

    return "\n".join(lineas)


def main():
    print(build_report())


if __name__ == "__main__":
    main()
