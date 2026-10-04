# Cripto Radar IA

Sistema de agentes que **analizan el mercado de criptomonedas y alertan por Telegram**.
Solo analiza y avisa. **Lucho decide siempre cuándo comprar o vender.**

Corre solo en **GitHub Actions**, cada 30 minutos. No hace falta tener la PC prendida.

---

## ⛔ REGLA DURA (W1) — NO ROMPER

El sistema **jamás** ejecuta compra/venta ni mueve fondos.

- Sin claves de exchange con permisos de trading (solo la API pública de CoinGecko, de solo lectura).
- Sin endpoints de orden/retiro en ningún script.
- Verificado 2026-09-23: `grep` de claves de exchange y funciones de orden → sin resultados.

Si alguna vez se agrega una función que ejecute operaciones, es una violación de esta regla: **no se hace.**

Corolario: como el sistema solo lee datos públicos, este repo puede ser público sin exponer nada.

---

## Componentes

| Archivo | Qué hace |
|---|---|
| `radar.py` | **Punto de entrada.** Corre los dos agentes, arma un mensaje y lo manda por Telegram |
| `opportunity_scanner.py` | Monitor de movimientos: escanea el top 100 y avisa de subidas y picos de volumen fuertes |
| `watchlist_analyst.py` | Analista 24/7: monitorea la watchlist (BTC, ETH, WLD, NEAR, XRP) |
| `notify.py` | Envía los mensajes por Telegram |
| `backtest.py` | Prueba las reglas del monitor contra 90 días de historia. Correrlo antes de tocar un umbral |
| `fetch_market.py` | Prueba suelta de conexión con CoinGecko |
| `.github/workflows/radar.yml` | El cron que lo corre cada 30 min |

## ⚠️ Lo que el radar NO es

Las alertas avisan que algo **ya se movió**, no que algo **va a subir**.

El backtest del 2026-10-03 (`backtest_resultados.md`) probó las tres reglas contra 90 días de historia del top 30: **ninguna le gana a la línea base** (la misma moneda en una hora cualquiera). Las de movimiento en 1h y pico de volumen rinden *peor* que el azar en los tres horizontes, porque llegan tarde: después del salto, la moneda en promedio devuelve parte.

Por eso el script se llama "monitor de movimientos" y no "buscador de oportunidades", y los umbrales están altos: el objetivo es avisar solo de lo que de verdad se sale de lo normal, con pocas alertas.

## 🧠 Briefing con LLM (v3)

| Qué | Cuándo | Archivo |
|---|---|---|
| Briefing diario de BTC y ETH + watchlist | 19:05 Perú (00:05 UTC) | `briefing.py`, workflow `briefing.yml` |
| Briefing extra por movimiento fuerte (±2,5× ATR en 24h, ~1/mes) | chequea cada 30 min | `evento.py`, dentro de `radar.yml` |
| Monitor del top 100 | cada 30 min, **solo avisa si detecta algo** | `radar.py` |

Flujo: `briefing_datos.py` (datos duros: Binance, Coin Metrics, alternative.me) → `briefing_llm.py` (redacta `openai/gpt-5.4-mini` vía OpenRouter, sin recomendar ni predecir) → `verificador_cifras.py` (marca ⚠️ si aparece una cifra que no está en los datos) → Telegram.

Regla de diseño: **el LLM redacta, no interpreta.** Las lecturas de signos (si entran o salen monedas de los exchanges, si el MVRV está caro o barato) las escribe el código. Pruebas: `test_verificador.py`, `test_evento.py`, `test_briefing_llm.py`.

**Horarios (desde 2026-10-04):** GitHub atrasa o saltea sus propios cron (el 03/10 corrió el radar cada 4-5 h y salteó el briefing). Los lanza puntual un **Worker de Cloudflare** (`cloudflare/worker.js`, Cron Triggers `7,37 * * * *` → `radar.yml` y `5 0 * * *` → `briefing.yml`) vía `workflow_dispatch`. El Worker usa un token fine-grained con un solo permiso (Actions read/write, solo este repo, vence el 03/10/2027) guardado como secret en Cloudflare. `radar.yml` conserva su cron de GitHub como respaldo; `briefing.yml` no, para no llegar duplicado.

Secrets necesarios: `TELEGRAM_TOKEN`, `TELEGRAM_CHAT_ID`, `OPENROUTER_API_KEY`. `estado_eventos.json` lo commitea el workflow cuando avisa de un evento: **antes de hacer push desde la PC, `git pull --rebase`**.

## 🔬 Investigación de swing trading (2026-10-03) — en pausa

Se buscó una señal de entrada para swing de 2-5 días en BTC y ETH (1% de riesgo, stop 1,5×ATR, objetivo 3×ATR, comisiones de Binance). Resultado: **ninguna señal le gana a entrar al azar**.

| Prueba | Archivo | Resultado |
|---|---|---|
| F1 — 3 estrategias × 2, 2020-2026 | `backtest_swing.py` → `backtest_swing_resultados.md` | Ninguna pasa el criterio fijado antes |
| F1b — 6 estrategias pre-registradas (técnicas + on-chain) | `PREREGISTRO.md`, `backtest_f1b.py` → `backtest_f1b_resultados.md` | Ninguna le gana al azar (p 0,23–0,94; vara 0,0083) |

La esperanza positiva que mostraban venía del filtro "BTC sobre su EMA200" (que evitó 2022) y de la estructura de salida: entrar al azar con eso mismo ya da ≈ +0,12 R. **El período 2024 → hoy no se usó**: queda limpio para probar una hipótesis nueva, una vez y con pre-registro.

`probe_fuentes.py` (+ workflow `probe.yml`): `api.binance.com` responde HTTP 451 desde GitHub Actions; `data-api.binance.vision` sí funciona.

## Credenciales

`notify.py` las busca en este orden:

1. **Variables de entorno** `TELEGRAM_TOKEN` y `TELEGRAM_CHAT_ID` — es lo que usa GitHub Actions.
2. **`config.json` local** — es lo que usa tu PC. Está en `.gitignore`, **nunca** se sube.

Para cargarlas en GitHub: *Settings → Secrets and variables → Actions → New repository secret*.
Hay que crear las dos, con esos nombres exactos.

## Cómo correr en tu PC

```
.venv/Scripts/python.exe radar.py
```

Usa `config.json`, manda a Telegram igual que en la nube.

## Cómo correr en la nube a mano

Pestaña **Actions** → *Cripto Radar* → **Run workflow**. Sirve para probar sin esperar al cron.

## Dos límites de GitHub Actions que conviene recordar

- ⏱️ **El cron se atrasa.** GitHub no garantiza puntualidad; en horas pico puede demorar 5-20 min.
- 😴 **60 días sin actividad** en el repo y GitHub desactiva los workflows programados (avisa por mail). Un commit cada tanto lo evita.

## Watchlist

BTC, ETH, WLD, NEAR, XRP — se edita en `WATCHLIST`, dentro de `watchlist_analyst.py`.
IDs de CoinGecko: `bitcoin`, `ethereum`, `worldcoin-wld`, `near`, `ripple`.

## Umbrales de señal

Se editan arriba de `opportunity_scanner.py`. **Antes de cambiar uno, correr `backtest.py`** para ver qué pasa con el ruido y con la ventaja.

| Constante | Valor | Antes del 2026-10-03 | Significa |
|---|---|---|---|
| `SIGNAL_24H` | 20.0 | 10.0 | subida de 24h que dispara alerta |
| `SIGNAL_1H` | 5.0 | 3.0 | movimiento de 1h que dispara alerta |
| `VOLUME_RATIO` | 0.35 | 0.15 | volumen/market cap que cuenta como pico |
| `MIN_MARKET_CAP` | 50M | 50M | piso para filtrar monedas sin liquidez |

## Cómo correr el backtest

```
.venv/Scripts/python.exe backtest.py
```

La primera vez baja la historia de CoinGecko (~5 min por el límite de llamadas) y la guarda en `data/`, que no se sube al repo. Las siguientes corridas salen del caché y son instantáneas. Para datos frescos, borrar `data/`. Genera `backtest_resultados.md`.

---

## Historial de despliegue

Primero se intentó un VPS gratuito de Oracle Cloud (ver `DEPLOY_ORACLE.md`). El 2026-10-02 falló:
los dos shapes de la capa gratuita (`VM.Standard.E2.1.Micro` y `VM.Standard.A1.Flex`) dieron
*"capacidad insuficiente"* en Santiago AD-1, que es la única región/AD donde esa cuenta tiene
recursos gratis. Se migró a GitHub Actions, que además no deja servidor que mantener.
