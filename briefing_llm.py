"""Cripto Radar IA - V3-2: el LLM redacta el briefing a partir del JSON de V3-1.

El LLM es un REDACTOR, no un analista que predice: recibe solo los datos
duros de briefing_datos.py y los resume con formato fijo, con argumentos a
favor y en contra. No recomienda, no predice, no ejecuta (regla dura W1).

Clave de OpenRouter, en orden de prioridad:
  1. Variable de entorno OPENROUTER_API_KEY   (GitHub Actions)
  2. "openrouter_api_key" en config.json      (tu PC; esta en .gitignore)
La clave nunca se imprime.

Uso:
    python briefing_llm.py                 (modelo por defecto)
    python briefing_llm.py --modelo <id>
    python briefing_llm.py --comparar <id1>,<id2>,<id3>   (mismo JSON a varios modelos)
"""
import argparse
import json
import os
import sys
import time

import requests

import briefing_datos

URL = "https://openrouter.ai/api/v1/chat/completions"
# Elegido por Lucho el 2026-10-03 tras comparar 4 modelos con el mismo JSON: fue el unico
# sin cifras inventadas y con todas las interpretaciones correctas. Version fija, no "-latest".
MODELO = "openai/gpt-5.4-mini"
HERE = os.path.dirname(os.path.abspath(__file__))

SISTEMA = """Sos el redactor del briefing diario de un monitor de criptomonedas personal. El lector es Lucho: decide él, a mano, si opera o no, después de mirar sus gráficos en TradingView. Tu trabajo es ahorrarle tiempo, no decirle qué hacer.

REGLAS (obligatorias):
1. Usá SOLO los números que aparecen en el JSON, tal cual (podés quitar decimales). No calcules cifras nuevas, no estimes, no completes con lo que sepas del mercado.
2. Si un dato falta o es null, escribí "sin datos". Nunca lo inventes.
3. Nunca recomiendes comprar, vender, entrar ni salir. Nunca des precios objetivo ni digas que algo "va a subir/bajar". Describí lo que muestran los datos.
4. Siempre dá argumentos A FAVOR y EN CONTRA, con la misma seriedad. Si los datos son mayormente positivos, buscá igual el riesgo.
5. Breve: máximo 170 palabras en total. Español neutro. Texto plano para Telegram: sin markdown, sin asteriscos, sin tablas.

FORMATO EXACTO (respetá los emojis y el orden):
📍 Qué pasó
(1-2 líneas por moneda: cierre, cambio 1d y 7d)
✅ A favor
(2-3 viñetas con "•")
❌ En contra
(2-3 viñetas con "•")
⚠️ Riesgos
(1-2 viñetas: datos extremos o faltantes)
👀 Qué mirar en el gráfico
(1-2 viñetas: niveles concretos del JSON, ej. máximo/mínimo de 20 días o las EMA)

CÓMO LEER EL JSON:
- cierre y cambio_*_pct: precio de cierre de la última vela diaria cerrada (fecha_vela) y su cambio porcentual.
- ema20/ema50/ema200 y sobre_emaX: medias móviles exponenciales y si el cierre está por encima. dist_ema200_pct: distancia porcentual a la EMA200.
- rsi14: índice de fuerza relativa (0-100). Más de 70 suele leerse como sobrecompra; menos de 30, sobreventa.
- atr_pct: volatilidad diaria típica, en % del precio.
- maximo_20d / minimo_20d: rango de los últimos 20 días.
- volumen_vs_prom_20d: volumen del día dividido por su promedio de 20 días (1,5 = 50% más de lo habitual).
- mvrv: precio de mercado sobre el costo promedio de los tenedores. mvrv_media_365d es su promedio del último año (más alto que la media = relativamente caro; más bajo = relativamente barato).
- flujo_neto_exchanges: monedas que entraron menos las que salieron de los exchanges (positivo = entran, posible presión de venta; negativo = salen). flujo_neto_z30: qué tan inusual es frente a los últimos 30 días (más de 2 o menos de -2 es inusual). fecha_onchain: estos datos llegan con un día de atraso.
- miedo_codicia: índice de sentimiento 0-100 (más de 75 codicia extrema, menos de 25 miedo extremo).
- mvrv_lectura, flujo_lectura y flujo_inusual: la interpretación YA HECHA de esos datos. Usala tal cual para describir el sentido (si entran o salen monedas, si el MVRV está caro o barato). No la deduzcas vos de los signos.
- regimen.btc_sobre_ema200: si BTC está sobre su EMA200.
- faltantes: fuentes que no respondieron hoy.

CONTEXTO IMPORTANTE: en los backtests de este proyecto, ninguno de estos indicadores anticipó subidas por sí solo mejor que el azar. Por eso describís, no predecís."""

PIE = "—\nResumen automático de datos públicos. No es una recomendación: decidís vos, mirando el gráfico."


def clave():
    k = os.environ.get("OPENROUTER_API_KEY")
    if k:
        return k
    ruta = os.path.join(HERE, "config.json")
    if os.path.exists(ruta):
        with open(ruta, encoding="utf-8") as f:
            k = json.load(f).get("openrouter_api_key")
    if not k:
        raise RuntimeError("Falta la clave: definí OPENROUTER_API_KEY o agregá 'openrouter_api_key' a config.json.")
    return k


def redactar(datos, modelo=MODELO):
    """Devuelve (texto, info) con el briefing y el uso de tokens/costo que informa OpenRouter."""
    cuerpo = {
        "model": modelo,
        "temperature": 0.2,
        "max_tokens": 700,
        "messages": [
            {"role": "system", "content": SISTEMA},
            {"role": "user", "content": "Datos de hoy:\n" + json.dumps(datos, ensure_ascii=False)},
        ],
        "usage": {"include": True},
    }
    t0 = time.time()
    r = requests.post(URL, json=cuerpo, timeout=120, headers={
        "Authorization": f"Bearer {clave()}",
        "HTTP-Referer": "https://github.com/Lcampos2015/cripto-radar",
        "X-Title": "Cripto Radar IA",
    })
    if r.status_code != 200:
        raise RuntimeError(f"OpenRouter HTTP {r.status_code}: {r.text[:200]}")
    j = r.json()
    texto = j["choices"][0]["message"]["content"].strip()
    uso = j.get("usage", {})
    info = {
        "modelo": j.get("model", modelo),
        "segundos": round(time.time() - t0, 1),
        "tokens_entrada": uso.get("prompt_tokens"),
        "tokens_salida": uso.get("completion_tokens"),
        "costo_usd": uso.get("cost"),
    }
    return texto + "\n\n" + PIE, info


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--modelo", default=MODELO)
    g.add_argument("--comparar", help="ids separados por coma")
    args = ap.parse_args()

    datos = briefing_datos.recolectar()
    modelos = [args.modelo] if args.modelo else [m.strip() for m in args.comparar.split(",")]
    for m in modelos:
        print("=" * 64)
        try:
            texto, info = redactar(datos, m)
            palabras = len(texto.replace(PIE, "").split())
            print(f"MODELO: {info['modelo']} | {info['segundos']}s | tokens {info['tokens_entrada']}+{info['tokens_salida']} "
                  f"| costo ${info['costo_usd']} | {palabras} palabras\n")
            print(texto)
        except Exception as e:
            print(f"MODELO: {m} -> ERROR {type(e).__name__}: {e}")
    print("=" * 64)


if __name__ == "__main__":
    main()
