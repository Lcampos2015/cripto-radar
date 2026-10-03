"""Cripto Radar IA - monitor de movimientos (v1).

Corre cada 30 minutos en GitHub Actions. Desde el 2026-10-03 solo manda un
mensaje cuando detecta movimientos (antes mandaba siempre: ~48 mensajes por
dia, y lo importante se perdia en el ruido). El informe de la watchlist paso
al briefing diario (briefing.py).

Si CoinGecko falla, se registra en el log y NO se manda nada: el briefing
diario de las 19:05 hace de senal de vida del sistema.

REGLA DURA (W1): solo analiza y avisa. Jamas ejecuta compra/venta.
"""
import sys
from datetime import datetime, timedelta, timezone

import notify
import opportunity_scanner
import watchlist_analyst

# Huancayo, Peru (UTC-5)
PERU = timezone(timedelta(hours=-5))


def build_message(lineas):
    ahora = datetime.now(PERU).strftime("%d/%m %H:%M")
    try:
        watchlist = watchlist_analyst.build_report()
    except Exception as e:
        watchlist = f"⚠ Analista: fallo ({type(e).__name__})"
    partes = [
        f"\U0001F4E1 CRIPTO RADAR - {ahora}",
        opportunity_scanner.build_report(lineas),
        watchlist,
        "—\nSolo analisis. Vos decidis cuando comprar o vender.",
    ]
    return "\n\n".join(partes)


def main():
    # Windows: la consola no siempre esta en UTF-8 y los emoji revientan el print
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

    try:
        lineas = opportunity_scanner.detectar()
    except Exception as e:
        print(f"Monitor: fallo CoinGecko ({type(e).__name__}: {e}). No se envia nada.")
        return

    if not lineas:
        print("Sin movimientos fuera de lo comun. No se envia nada.")
        return

    mensaje = build_message(lineas)
    print(mensaje)
    print("\n--- enviando a Telegram ---")
    print("Enviado:", notify.send_telegram(mensaje))


if __name__ == "__main__":
    main()
