# Backtest de señales — Cripto Radar IA

Generado: 2026-10-03 05:44 UTC · Período: 2026-07-06 → 2026-10-03 · Universo: 30 monedas (top por cap, sin stablecoins) · Datos por hora

## 1. Con los umbrales actuales

Umbrales: SUBIDA 24h ≥ 20% · MOV 1h ≥ 5% · PICO VOL ≥ 35% del cap

**Monedas con alerta por pasada (promedio): 0.4** sobre 30 monedas y 2137 horas.

| Señal | Disparos por pasada | Eventos | Acierto 24h | Mediana 24h | Exceso vs base 24h | Le gana a la base | Veredicto |
|---|---|---|---|---|---|---|---|
| SUBIDA 24h | 0.27 | 44 | 57% | +3.53% | +1.37% | 52% | ruido |
| MOV 1h | 0.09 | 76 | 59% | +1.54% | +0.05% | 50% | ruido |
| PICO VOL | 0.11 | 11 | 36% | -2.43% | -3.03% | 36% | muestra chica, sin conclusión |
| *Línea base (hora cualquiera)* | — | — | 51% | +0.05% | 0 | 50% | referencia |

### Todos los horizontes

| Señal | Horizonte | n | Acierto | Mediana | Exceso vs base | Le gana a la base |
|---|---|---|---|---|---|---|
| SUBIDA 24h | +4h | 44 | 50% | +0.01% | -0.48% | 48% |
| SUBIDA 24h | +24h | 44 | 57% | +3.53% | +1.37% | 52% |
| SUBIDA 24h | +7d | 38 | 63% | +11.97% | -2.77% | 45% |
| MOV 1h | +4h | 76 | 45% | -0.28% | -0.60% | 41% |
| MOV 1h | +24h | 74 | 59% | +1.54% | +0.05% | 50% |
| MOV 1h | +7d | 65 | 74% | +6.44% | -2.26% | 45% |
| PICO VOL | +4h | 11 | 45% | -0.58% | -0.67% | 45% |
| PICO VOL | +24h | 11 | 36% | -2.43% | -3.03% | 36% |
| PICO VOL | +7d | 10 | 60% | +7.96% | -2.26% | 50% |
| *Línea base* | +4h | — | 50% | +0.00% | 0 | 50% |
| *Línea base* | +24h | — | 51% | +0.05% | 0 | 50% |
| *Línea base* | +7d | — | 56% | +0.67% | 0 | 50% |

## 2. Barrido de umbrales

Se cambia **un umbral a la vez**; los otros quedan como están. Mide qué pasa con el ruido (disparos) y con la ventaja (exceso a 24h).

| Regla | Umbral | Disparos por pasada | Eventos | Exceso vs base 24h | Le gana a la base 24h | Veredicto |
|---|---|---|---|---|---|---|
| PICO VOL | 15% cap | 1.26 | 36 | -1.95% | 36% | peor que el azar |
| PICO VOL | 25% cap | 0.33 | 19 | +0.95% | 63% | muestra chica, sin conclusión |
| PICO VOL | 35% cap (actual) | 0.11 | 11 | -3.03% | 36% | muestra chica, sin conclusión |
| PICO VOL | 50% cap | 0.02 | 3 | -3.67% | 0% | muestra chica, sin conclusión |
| SUBIDA 24h | 10% | 0.94 | 123 | -0.04% | 49% | ruido |
| SUBIDA 24h | 15% | 0.47 | 65 | -0.95% | 46% | ruido |
| SUBIDA 24h | 20% (actual) | 0.27 | 44 | +1.37% | 52% | ruido |
| MOV 1h | 3% | 0.26 | 189 | -1.14% | 41% | peor que el azar |
| MOV 1h | 4% | 0.14 | 129 | -0.66% | 44% | peor que el azar |
| MOV 1h | 5% (actual) | 0.09 | 76 | +0.05% | 50% | ruido |

## 3. Cómo leer esto

- **Disparos por pasada**: cuántas alertas de ese tipo te llegan cada vez que corre el radar. Es el ruido.
- **Eventos**: primer disparo después de 24h sin disparar. Es la muestra real con la que se mide si la señal sirve.
- **Exceso vs base**: rendimiento después de la señal **menos** el rendimiento promedio de esa misma moneda en una hora cualquiera. Positivo = la señal anticipa algo.
- **Le gana a la base**: % de eventos con exceso positivo. 50% es una moneda al aire.
- **Veredicto** (a 24h): *ventaja* si el exceso es positivo y le gana a la base ≥55% de las veces; *peor que el azar* si es negativo y le gana ≤45%; *muestra chica* con menos de 20 eventos; *ruido* en el resto.

## 4. Límites — leer antes de decidir

- 🪞 **Sesgo de supervivencia.** El universo es el top de *hoy*. Las monedas que se fundieron en el período no están, y eso infla los resultados.
- 📉 **Un solo régimen de mercado.** 90 días no dicen nada sobre un mercado distinto al de este período.
- ⏱️ **Datos por hora.** El radar en vivo corre cada 30 min; acá se evalúa una vez por hora.
- 🧮 **Muchas pruebas a la vez.** Con 3 reglas × 3 horizontes × varios umbrales, alguna va a salir "buena" por casualidad. Un resultado aislado no alcanza: tiene que ser consistente entre horizontes.
- ⛔ **No es una estrategia de trading.** No hay comisiones, deslizamiento ni gestión de riesgo. Solo responde si la señal anticipa movimiento.
