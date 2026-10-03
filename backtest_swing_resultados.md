# Backtest swing — Cripto Radar IA (F1)

Generado: 2026-10-03 13:15 UTC · Velas diarias Binance (data-api.binance.vision) · BTC y ETH · 2020-01-01 → 2026-10-02 (6.8 años)

Reglas F0: capital inicial $100 · riesgo 1% por operación · stop 1.5×ATR · objetivo 3.0×ATR · máx. 5 días · 1 operación a la vez · freno −10% mensual · comisión 0.1% por lado · sin apalancamiento

## Línea base: comprar y no tocar

| | Retorno total | Anual (CAGR) | Caída máxima | Anual ÷ caída |
|---|---|---|---|---|
| Mantener BTC | +1074.6% | +44.0% | 76.6% | 0.57 |
| Mantener ETH | +1966.1% | +56.6% | 79.3% | 0.71 |

## Criterio para pasar (fijado antes de correr)

1. **Esperanza > 0**: en promedio gana algo por cada $1 que arriesga, ya descontadas las comisiones.
2. **≥ 30 operaciones**.
3. **Positiva en la mayoría de los años** con operaciones.
4. **Anual ÷ caída mejor que mantener BTC y que mantener ETH** (la vara: 0.71).

## Resultados

| Estrategia | Ops | Ganadoras | Esperanza (R) | Años + | Anual | Caída máx. | Anual ÷ caída | Expuesto | 1 | 2 | 3 | 4 | **Pasa** |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Tendencia | 88 | 48% | +0.04 | 3/7 | +0.5% | 11.9% | 0.04 | 15% | ✅ | ✅ | ❌ | ❌ | **❌** |
| Tendencia + filtro BTC | 82 | 48% | +0.06 | 3/6 | +0.6% | 10.4% | 0.06 | 14% | ✅ | ✅ | ❌ | ❌ | **❌** |
| Ruptura | 144 | 52% | +0.19 | 4/7 | +4.0% | 9.0% | 0.44 | 24% | ✅ | ✅ | ✅ | ❌ | **❌** |
| Ruptura + filtro BTC | 117 | 53% | +0.23 | 5/7 | +3.9% | 7.5% | 0.52 | 19% | ✅ | ✅ | ✅ | ❌ | **❌** |
| Rebote | 3 | 67% | -0.05 | 2/3 | -0.0% | 1.5% | -0.01 | 0% | ❌ | ❌ | ✅ | ❌ | **❌** |
| Rebote + filtro BTC | 3 | 67% | -0.05 | 2/3 | -0.0% | 1.5% | -0.01 | 0% | ❌ | ❌ | ✅ | ❌ | **❌** |

### Resultado por año (suma de R)

| Estrategia | 2020 | 2021 | 2022 | 2023 | 2024 | 2025 | 2026 |
|---|---|---|---|---|---|---|---|
| Tendencia | +6.1 | -2.2 | -1.0 | -1.1 | -0.8 | +0.6 | +2.2 |
| Tendencia + filtro BTC | +6.1 | -1.6 | — | -1.1 | -0.8 | +0.6 | +1.6 |
| Ruptura | +8.7 | +9.8 | -0.5 | +9.4 | +2.9 | -1.1 | -1.8 |
| Ruptura + filtro BTC | +9.3 | +7.9 | -0.2 | +5.5 | +2.9 | -0.1 | +1.5 |
| Rebote | — | — | — | -1.0 | +0.3 | +0.6 | — |
| Rebote + filtro BTC | — | — | — | -1.0 | +0.3 | +0.6 | — |

### Cómo terminaron las operaciones

| Estrategia | Objetivo | Stop | Día 5 | Frenos mensuales | Capital final |
|---|---|---|---|---|---|
| Tendencia | 9 | 26 | 53 | 0 | $103.25 |
| Tendencia + filtro BTC | 9 | 25 | 48 | 0 | $104.37 |
| Ruptura | 26 | 46 | 72 | 0 | $130.37 |
| Ruptura + filtro BTC | 22 | 37 | 58 | 0 | $129.52 |
| Rebote | 0 | 1 | 2 | 0 | $99.85 |
| Rebote + filtro BTC | 0 | 1 | 2 | 0 | $99.85 |

## Cómo leer esto

- **R** = lo que arriesgás por operación (1% del capital). Esperanza +0,10 R = en promedio ganás 10 centavos por cada $1 arriesgado.
- **Anual ÷ caída**: cuánto rinde por año en relación al peor bajón que tuviste que aguantar. Es la forma justa de comparar contra mantener, porque la estrategia está invertida solo una parte del tiempo (columna *Expuesto*).
- **Años +**: años con resultado positivo sobre años con operaciones.

## Límites — leer antes de decidir

- 🧮 **6 variantes a la vez.** Alguna puede pasar por suerte. La que pase tiene que ser consistente año a año, y después confirmarse en paper trading (F3).
- 📉 **Deslizamiento no modelado.** Se asume que entrás exactamente en la apertura y salís exactamente en el stop u objetivo (salvo gaps). En la vida real es un poco peor.
- ⚖️ **Si el mismo día se tocan stop y objetivo, se asume el stop** (supuesto conservador: con velas diarias no se sabe cuál fue primero).
- 🕰️ **El pasado no garantiza nada.** Esto mide si la regla tuvo ventaja en 2020-2026, no si la va a tener.
- ⛔ **Es simulación.** Ninguna línea de este código opera (W1).

## Veredicto

**Ninguna estrategia pasa las cuatro condiciones.**
