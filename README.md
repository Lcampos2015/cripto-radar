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
| `opportunity_scanner.py` | Buscador: escanea el top 100, detecta subidas y picos de volumen |
| `watchlist_analyst.py` | Analista 24/7: monitorea la watchlist (BTC, ETH, WLD, NEAR, XRP) |
| `notify.py` | Envía los mensajes por Telegram |
| `fetch_market.py` | Prueba suelta de conexión con CoinGecko |
| `.github/workflows/radar.yml` | El cron que lo corre cada 30 min |

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

Se editan arriba de `opportunity_scanner.py`:

| Constante | Valor | Significa |
|---|---|---|
| `SIGNAL_24H` | 10.0 | subida de 24h que dispara señal |
| `SIGNAL_1H` | 3.0 | movimiento de 1h que dispara señal |
| `VOLUME_RATIO` | 0.15 | volumen/market cap que cuenta como pico |
| `MIN_MARKET_CAP` | 50M | piso para filtrar monedas sin liquidez |

---

## Historial de despliegue

Primero se intentó un VPS gratuito de Oracle Cloud (ver `DEPLOY_ORACLE.md`). El 2026-10-02 falló:
los dos shapes de la capa gratuita (`VM.Standard.E2.1.Micro` y `VM.Standard.A1.Flex`) dieron
*"capacidad insuficiente"* en Santiago AD-1, que es la única región/AD donde esa cuenta tiene
recursos gratis. Se migró a GitHub Actions, que además no deja servidor que mantener.
