# F1b — Protocolo anti-casualidad: resultados

Generado: 2026-10-03 13:34 UTC · Pre-registro: `PREREGISTRO.md` (commit 4707a82) · Exploración 2020-01-01 → 2023-12-31 · Test al azar: 1000 simulaciones, semilla 20261003 · Vara contra el azar p < 0.0083

## Línea base en exploración (mantener sin tocar)

| | Anual | Caída máx. | Anual ÷ caída |
|---|---|---|---|
| Mantener BTC | +55.7% | 76.6% | 0.73 |
| Mantener ETH | +105.1% | 79.3% | 1.33 |

## Exploración 2020–2023: las 7 condiciones

| Estrategia | Ops | Esperanza | 1 Esp>0 | 2 ≥30 ops | 3 Años + | 4 BTC y ETH | 5 Vecinos | 6 Azar (p) | 7 Anual÷caída | **Sobrevive** |
|---|---|---|---|---|---|---|---|---|---|---|
| 🪃 Retroceso en tendencia | 85 | -0.00 R | ❌ | ✅ | ❌ 1/4 | ❌ BTC -0.06 / ETH +0.06 | ✅ +0.04 / +0.02 | ❌ 0.943 | ❌ 0.01 vs 1.33 | **❌** |
| 〰️ Cruce MACD | 43 | +0.17 R | ✅ | ✅ | ✅ 3/4 | ✅ BTC +0.32 / ETH +0.02 | ✅ +0.29 / +0.37 | ❌ 0.357 | ❌ 0.54 vs 1.33 | **❌** |
| 🎈 Rebote Bollinger | 16 | +0.30 R | ✅ | ❌ | ✅ 3/4 | ✅ BTC +0.41 / ETH +0.12 | ✅ +0.13 / +0.14 | ❌ 0.228 | ❌ 0.57 vs 1.33 | **❌** |
| 🗜️ Compresión NR | 68 | +0.16 R | ✅ | ✅ | ✅ 3/4 | ✅ BTC +0.14 / ETH +0.20 | ✅ +0.20 / +0.12 | ❌ 0.348 | ❌ 0.33 vs 1.33 | **❌** |
| 🏦 Salida masiva de exchanges | 52 | +0.12 R | ✅ | ✅ | ✅ 4/4 | ❌ BTC -0.02 / ETH +0.35 | ✅ +0.10 / +0.02 | ❌ 0.516 | ❌ 0.32 vs 1.33 | **❌** |
| 📊 Barato + gatillo | 12 | +0.32 R | ✅ | ❌ | ❌ 2/4 | ❌ BTC +0.43 / ETH -0.02 | ❌ -0.13 / +0.52 | ❌ 0.245 | ❌ 0.27 vs 1.33 | **❌** |

### Detalle por año (suma de R, por año de entrada)

| Estrategia | 2020 | 2021 | 2022 | 2023 | Azar: esperanza mediana |
|---|---|---|---|---|---|
| 🪃 Retroceso en tendencia | +5.6 | -4.3 | — | -0.6 | +0.13 R |
| 〰️ Cruce MACD | +4.4 | +1.1 | — | +1.7 | +0.12 R |
| 🎈 Rebote Bollinger | +0.6 | +2.3 | — | +1.9 | +0.13 R |
| 🗜️ Compresión NR | +7.5 | +2.8 | -0.2 | +1.0 | +0.12 R |
| 🏦 Salida masiva de exchanges | +3.8 | +0.5 | +0.6 | +1.2 | +0.12 R |
| 📊 Barato + gatillo | +2.0 | -0.6 | — | +2.4 | +0.13 R |

## Caja fuerte (2024 → hoy)

🔒 **Ninguna estrategia sobrevivió la exploración, así que la caja fuerte NO se abrió.** Los datos 2024-hoy siguen limpios para un pre-registro futuro.

## Notas

- **Esperanza (R):** ganancia promedio por cada $1 arriesgado, neta de comisiones.
- **Azar (p):** proporción de simulaciones con entradas aleatorias (mismas salidas, tamaño, filtro y freno) que igualaron o superaron a la estrategia. Chico = la señal aporta.
- **Vecinos:** esperanza con todos los parámetros ×0,75 / ×1,25.
- Una operación abierta el último día de un período se cierra con hasta 5 días de datos posteriores.
- Fundamentales con 1 día de desfase. Solo simulación: nada opera (W1).
