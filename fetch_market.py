"""Cripto Radar IA - M2: prueba de conexion con CoinGecko API."""
import requests

URL = "https://api.coingecko.com/api/v3/coins/markets"
PARAMS = {
    "vs_currency": "usd",
    "order": "market_cap_desc",
    "per_page": 10,
    "page": 1,
    "sparkline": "false",
}

def main():
    r = requests.get(URL, params=PARAMS, timeout=15)
    r.raise_for_status()
    data = r.json()
    print(f"OK - {len(data)} monedas recibidas\n")
    print(f"{'Moneda':<12}{'Precio (USD)':<14}{'% 24h':<9}{'Volumen 24h':<16}")
    print("-" * 55)
    for c in data:
        print(
            f"{c['symbol'].upper():<12}"
            f"${c['current_price']:<13,.2f}"
            f"{c['price_change_percentage_24h']:>6.2f}%  "
            f"${c['total_volume']:>13,.0f}"
        )

if __name__ == "__main__":
    main()
