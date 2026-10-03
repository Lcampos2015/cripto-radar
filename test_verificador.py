"""Pruebas de V3-3 (verificador_cifras.py). Sin red: usa el JSON congelado del 2026-10-02.

Los tres primeros casos son briefings REALES de la comparacion de modelos del
2026-10-03, redactados con exactamente estos datos. El resultado esperado se
escribio antes de correr las pruebas.
"""
import copy
import json
import os
import sys

from verificador_cifras import anotar, verificar

HERE = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(HERE, "fixtures", "datos_2026-10-02.json"), encoding="utf-8") as f:
    DATOS = json.load(f)

HAIKU = """📍 Qué pasó
BTC cerró en 84518, cayó 0.43% en el día pero suma 0.5% en 7 días y 9.28% en 30 días. ETH en 2668, bajó 1.4% hoy, -0.86% en semana, pero +11.57% en mes.
✅ A favor
• Ambas monedas cotizan por encima de sus tres medias móviles (EMA20, EMA50, EMA200). BTC 13.21% arriba de la EMA200, ETH 17.22%.
• Volumen elevado: BTC 71% por encima del promedio de 20 días, ETH 54% arriba. Señal de participación.
❌ En contra
• MVRV de BTC en 1.57, por encima de su media anual (1.46): precio relativamente caro.
⚠️ Riesgos
• RSI de BTC en 63 y ETH en 58.8: zona neutra.
• Flujo neto de ETH positivo (40960.6): monedas entrando a exchanges.
👀 Qué mirar en el gráfico
• BTC: máximo de 20 días en 87395, mínimo en 74967.
• ETH: máximo en 2807, mínimo en 2358. Distancia a máximo: 49 puntos."""

GPT = """📍 Qué pasó
BTC cerró en 84518.01, -0.43% 1d y +0.5% 7d.
ETH cerró en 2668.59, -1.4% 1d y -0.86% 7d.
✅ A favor
• BTC y ETH están sobre EMA20, EMA50 y EMA200.
• BTC: RSI 63, volumen 1.71 y cierre sobre EMA200 con distancia de 13.21.
• ETH: RSI 58.8 y volumen 1.54; ambos mantienen cambio 30d positivo.
❌ En contra
• BTC cayó 1d y quedó debajo de su máximo 20d de 87395.67.
• ETH tuvo flujo neto a exchanges positivo: 40960.6.
⚠️ Riesgos
• BTC MVRV 1.57 vs media 365d 1.46; ETH 1.14 vs 1.02.
• Miedo/codicia en 67: sesgo de codicia, no extremo.
👀 Qué mirar en el gráfico
• BTC: EMA20 82473.98 y mínimo 20d 74967.97.
• ETH: EMA20 2631.67 y mínimo 20d 2358.88."""

DEEPSEEK = """📍 Qué pasó
BTC cerró en 84518 (-0.43% en 1d, +0.5% en 7d). ETH cerró en 2668 (-1.4% en 1d, -0.86% en 7d).
✅ A favor
• Volumen BTC 1.71x su promedio de 20d; ETH 1.54x.
• BTC: flujo neto de exchanges -3307.6 (salen monedas); MVRV 1.57 vs media 365d 1.46.
❌ En contra
• ETH: flujo neto +40960.6 (entran monedas), z30 0.92; MVRV 1.14 sobre media 1.02.
⚠️ Riesgos
• ATR diario: BTC 2.76%, ETH 3.5%.
• Flujo BTC z30 -0.09: movimiento poco inusual."""

SIN_ONCHAIN = copy.deepcopy(DATOS)
for m in SIN_ONCHAIN["monedas"].values():
    for k in ("fecha_onchain", "mvrv", "mvrv_media_365d", "flujo_neto_exchanges", "flujo_neto_z30"):
        m.pop(k, None)

# (nombre, texto, datos, dudosas esperadas)
CASOS = [
    ("Haiku real: 1 inventada + 2 calculadas", HAIKU, DATOS, ["71", "54", "49"]),
    ("GPT-5.4 mini real: limpio", GPT, DATOS, []),
    ("DeepSeek real: limpio (su error fue de interpretación)", DEEPSEEK, DATOS, []),
    ("Coma decimal y miles europeos", "BTC cerró en 84.518,01 y ETH en 2.668,59; -0,43% y +9,28%.", DATOS, []),
    ("Miles con coma", "BTC: 84,518.01 y máximo 87,395.67.", DATOS, []),
    ("Precio inventado", "BTC podría tocar 90000 pronto.", DATOS, ["90000"]),
    ("RSI con decimales que no están", "RSI de BTC en 62,97.", DATOS, ["62,97"]),
    ("Fechas: una real, una inventada", "Vela del 02/10 y 2026-10-02; dato del 05/10.", DATOS, ["05/10"]),
    ("Sin on-chain: MVRV inventado", "MVRV de BTC en 1.57.", SIN_ONCHAIN, ["1.57"]),
    ("Sin on-chain: texto honesto", "On-chain sin datos. BTC a 13,21% de la EMA200, ATR 2,76%.", SIN_ONCHAIN, []),
    ("Etiquetas no son cifras", "EMA20, EMA200, RSI14, z30, rango de 20 días y media de 365d.", DATOS, []),
    # Agregados tras el primer intento (bug de tolerancia): un entero vale solo si es redondeo o recorte exacto
    ("Entero cercano pero falso", "BTC subió 10% en el mes.", DATOS, ["10"]),
    ("Entero bien redondeado y recortado", "BTC +9% en el mes; RSI 63; cierre 84518.", DATOS, []),
    # Agregado tras la prueba forzada de V3-7: "EMA20/50/200" se leia como la fecha 20/50
    ("Medias escritas con barras no son fechas", "Sigue sobre EMA20/50/200 y sobre 20/50/200.", DATOS, []),
    ("Fecha inválida tratada como números", "Dato del 33/10.", DATOS, ["33", "10"]),
]


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    ok = 0
    for nombre, texto, datos, esperado in CASOS:
        obtenido = verificar(texto, datos)
        bien = sorted(obtenido) == sorted(esperado)
        ok += bien
        print(f"[{'OK ' if bien else 'MAL'}] {nombre:<52} esperado {esperado}  obtenido {obtenido}")
    print(f"\n{ok}/{len(CASOS)} casos OK")
    print("\nAsí se vería el de Haiku:\n")
    print(anotar(HAIKU, verificar(HAIKU, DATOS)).split("\n")[0])
    return ok == len(CASOS)


if __name__ == "__main__":
    sys.exit(0 if main() else 1)
