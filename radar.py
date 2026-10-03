"""Cripto Radar IA - orquestador.

Corre los dos agentes, arma un solo mensaje y lo manda por Telegram.
Es el punto de entrada que usa GitHub Actions (y el que podes correr a mano).

REGLA DURA (W1): solo analiza y avisa. Jamas ejecuta compra/venta.
"""
import sys
from datetime import datetime, timedelta, timezone

import notify
import opportunity_scanner
import watchlist_analyst

# Huancayo, Peru (UTC-5)
PERU = timezone(timedelta(hours=-5))


def seccion(nombre, fn):
    """Corre un agente y devuelve su informe; si falla, lo reporta sin tumbar el resto."""
    try:
        return fn()
    except Exception as e:
        return f"⚠ {nombre}: fallo ({type(e).__name__}: {e})"


def build_message():
    ahora = datetime.now(PERU).strftime("%d/%m %H:%M")
    partes = [
        f"\U0001F4E1 CRIPTO RADAR - {ahora}",
        seccion("Movimientos", opportunity_scanner.build_report),
        seccion("Analista", watchlist_analyst.build_report),
        "—\nSolo analisis. Vos decidis cuando comprar o vender.",
    ]
    return "\n\n".join(partes)


def main():
    # Windows: la consola no siempre esta en UTF-8 y los emoji revientan el print
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

    mensaje = build_message()
    print(mensaje)
    print("\n--- enviando a Telegram ---")
    print("Enviado:", notify.send_telegram(mensaje))


if __name__ == "__main__":
    main()
