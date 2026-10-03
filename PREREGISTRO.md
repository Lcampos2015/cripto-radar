# F1b — Pre-registro de estrategias (protocolo anti-casualidad)

🔒 **Registrado el 2026-10-03, ANTES de escribir el código y de ver cualquier resultado.** Aprobado por Lucho.

**Regla:** desde acá no se agrega ninguna estrategia ni se cambia ningún parámetro o umbral. Cualquier cambio exige un pre-registro nuevo, con fecha, y el período sellado ya no cuenta como limpio para lo que se haya mirado.

Este archivo es la copia del pre-registro guardado en el vault de Lucho. La fecha del commit demuestra que se escribió antes que el código.

## Por qué existe

En F1 ninguna estrategia pasó, y Lucho pidió probar otras "afinándolo bien para evitar la casualidad". Cuantas más estrategias se prueban, más probable que alguna salga bien por suerte. Este protocolo pone cuatro barreras contra eso: lista cerrada, datos sellados, comparación contra el azar y robustez de parámetros.

## Datos

- **Precios:** velas diarias de Binance spot (`data-api.binance.vision`), BTCUSDT y ETHUSDT.
- **Fundamentales:** Coin Metrics community API (gratis) — `CapMVRVCur`, `FlowInExNtv`, `FlowOutExNtv`, por activo.
- **Desfase de 1 día en los fundamentales:** la señal al cierre del día *i* usa el dato del día *i−1*, porque el del día *i* puede no estar publicado a las 19:00 de Perú. Evita mirar el futuro sin querer.

## Períodos

| Período | Fechas | Uso |
|---|---|---|
| 🔍 **Exploración** | 2020-01-01 → 2023-12-31 | Se mira libremente, y solo con esto se decide qué pasa a la caja fuerte |
| 🔒 **Sellado** | 2024-01-01 → fecha de la corrida | Una sola corrida, solo para las que sobrevivan |

*Contaminación admitida:* ya vimos el mercado general de 2024-2026 (precios, noticias) y las 6 variantes de F1 en todo el período. Por eso esas 6 quedan afuera, y las nuevas salen de manuales, no de mirar esos años.

## Reglas comunes (F0, sin cambios)

Entrada en la apertura del día siguiente a la señal · stop 1,5×ATR(14) · objetivo 3×ATR(14) · salida forzada al día 5 · riesgo 1% · 1 operación a la vez (si las dos monedas dan señal, BTC primero) · freno −10% mensual · comisión 0,1% por lado · sin apalancamiento · **filtro BTC > su EMA200 en las 6**.

## Las 6 estrategias

| # | Estrategia | Señal al cierre del día *i* | Parámetros | Vecino −25% | Vecino +25% |
|---|---|---|---|---|---|
| 1 | 🪃 Retroceso en tendencia | EMAr > EMAl > EMA200, mínimo ≤ EMAr y cierre > EMAr | r=20, l=50 | 15, 38 | 25, 63 |
| 2 | 〰️ Cruce MACD | la línea MACD cruza hacia arriba la línea de señal | 12, 26, 9 | 9, 20, 7 | 15, 33, 11 |
| 3 | 🎈 Rebote Bollinger | cierre de ayer bajo la banda inferior y cierre de hoy arriba | n=20, k=2,0σ | 15, 1,5σ | 25, 2,5σ |
| 4 | 🗜️ Compresión NR | ayer tuvo el rango (máx−mín) más chico de los últimos N días, y hoy cierra arriba del máximo de ayer | N=7 | 5 | 9 |
| 5 | 🏦 Salida masiva de exchanges | flujo neto (entradas − salidas) con z-score ≤ umbral, contra su media y desvío de los W días previos | W=30, z ≤ −2,0 | 22, −1,5 | 38, −2,5 |
| 6 | 📊 Barato + gatillo | MVRV < su media de los M días previos **y** el cierre cruza arriba de la EMAg | M=365, g=20 | 274, 15 | 456, 25 |

En los vecinos se escalan **juntos** todos los parámetros de la estrategia (×0,75 y ×1,25, redondeado).

## Condiciones en exploración (2020–2023) — hay que cumplir las 7

1. **Esperanza > 0 R**, neta de comisiones.
2. **≥ 30 operaciones.**
3. **Positiva en al menos 3 de los 4 años.**
4. **Positiva en BTC y en ETH por separado.** Si una moneda no tiene operaciones, no cumple.
5. **Los dos vecinos (±25%) con esperanza > 0.**
6. **Le gana al azar:** 1000 simulaciones con entradas aleatorias (mismas salidas, mismo tamaño, mismos filtros y freno, moneda al azar, misma frecuencia de entrada que la estrategia). Con *k* = simulaciones con esperanza ≥ la de la estrategia, p = (k+1)/1001. **Pasa si p < 0,0083** (0,05 ÷ 6, por probar 6 estrategias).
7. **Anual ÷ caída máxima mayor que mantener BTC y que mantener ETH** en el mismo período.

## Caja fuerte (2024 → hoy) — una sola corrida, solo sobrevivientes

1. Esperanza > 0 R.
2. ≥ 15 operaciones.
3. Le gana al azar con p < 0,05 ÷ (cantidad de sobrevivientes).

Si pasa → F2/F3 (alertas y *paper trading*). Si no pasa → se descarta. **No se reintenta con otros parámetros.**

## Resultado posible y válido

Que no pase ninguna. Sería un resultado, no un fracaso: evita arriesgar plata en algo sin ventaja.
