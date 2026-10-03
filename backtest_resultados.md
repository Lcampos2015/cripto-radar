# Backtest de señales — Cripto Radar IA

Generado: 2026-10-03 05:34 UTC · Período: 2026-07-06 → 2026-10-03 · Universo: 30 monedas (top por cap, sin stablecoins) · Datos por hora

## 1. Con los umbrales actuales

Umbrales: SUBIDA 24h ≥ 10% · MOV 1h ≥ 3% · PICO VOL ≥ 15% del cap

**Monedas con alerta por pasada (promedio): 2.0** sobre 30 monedas y 2137 horas.

| Señal | Disparos por pasada | Eventos | Acierto 24h | Mediana 24h | Exceso vs base 24h | Le gana a la base | Veredicto |
|---|---|---|---|---|---|---|---|
| SUBIDA 24h | 0.94 | 123 | 54% | +0.91% | -0.04% | 49% | ruido |
| MOV 1h | 0.26 | 189 | 49% | -0.12% | -1.14% | 41% | peor que el azar |
| PICO VOL | 1.26 | 36 | 42% | -1.15% | -1.95% | 36% | peor que el azar |
| *Línea base (hora cualquiera)* | — | — | 51% | +0.05% | 0 | 50% | referencia |

### Todos los horizontes

| Señal | Horizonte | n | Acierto | Mediana | Exceso vs base | Le gana a la base |
|---|---|---|---|---|---|---|
| SUBIDA 24h | +4h | 123 | 49% | -0.07% | -0.29% | 48% |
| SUBIDA 24h | +24h | 123 | 54% | +0.91% | -0.04% | 49% |
| SUBIDA 24h | +7d | 112 | 68% | +5.72% | -1.31% | 48% |
| MOV 1h | +4h | 189 | 43% | -0.28% | -0.57% | 37% |
| MOV 1h | +24h | 184 | 49% | -0.12% | -1.14% | 41% |
| MOV 1h | +7d | 166 | 55% | +1.50% | -1.92% | 41% |
| PICO VOL | +4h | 36 | 47% | -0.18% | -0.22% | 47% |
| PICO VOL | +24h | 36 | 42% | -1.15% | -1.95% | 36% |
| PICO VOL | +7d | 32 | 50% | +0.56% | -2.58% | 41% |
| *Línea base* | +4h | — | 50% | +0.00% | 0 | 50% |
| *Línea base* | +24h | — | 51% | +0.05% | 0 | 50% |
| *Línea base* | +7d | — | 56% | +0.67% | 0 | 50% |

## 2. Barrido de umbrales

Se cambia **un umbral a la vez**; los otros quedan como están. Mide qué pasa con el ruido (disparos) y con la ventaja (exceso a 24h).

| Regla | Umbral | Disparos por pasada | Eventos | Exceso vs base 24h | Le gana a la base 24h | Veredicto |
|---|---|---|---|---|---|---|
| PICO VOL | 15% cap (actual) | 1.26 | 36 | -1.95% | 36% | peor que el azar |
| PICO VOL | 25% cap | 0.33 | 19 | +0.95% | 63% | muestra chica, sin conclusión |
| PICO VOL | 35% cap | 0.11 | 11 | -3.03% | 36% | muestra chica, sin conclusión |
| PICO VOL | 50% cap | 0.02 | 3 | -3.67% | 0% | muestra chica, sin conclusión |
| SUBIDA 24h | 10% (actual) | 0.94 | 123 | -0.04% | 49% | ruido |
| SUBIDA 24h | 15% | 0.47 | 65 | -0.95% | 46% | ruido |
| SUBIDA 24h | 20% | 0.27 | 44 | +1.37% | 52% | ruido |
| MOV 1h | 3% (actual) | 0.26 | 189 | -1.14% | 41% | peor que el azar |
| MOV 1h | 4% | 0.14 | 129 | -0.66% | 44% | peor que el azar |
| MOV 1h | 5% | 0.09 | 76 | +0.05% | 50% | ruido |

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
