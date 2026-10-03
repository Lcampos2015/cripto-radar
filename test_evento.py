"""Pruebas de V3-7: la regla de decision de evento.py (funcion pura, sin red).

El 2026-10-03 se vio que GitHub corre el radar cada 4-5 horas, no cada 30 min.
Los casos "cron atrasado" cubren el bug que eso destapo: un cruce de hace 3h
se tomaba como "ya venia superado" y el evento no se avisaba nunca.
"""
import sys

from evento import decidir

H = 3600_000
AHORA = 1_000 * H
UMBRAL = 7.0


def serie(valores_por_hora_atras):
    """{horas_atras: pct} -> [(ms, pct)] ordenado; el de 0 horas atras es 'ahora'."""
    return sorted((AHORA - h * H, p) for h, p in valores_por_hora_atras.items())


def hace(horas):
    return AHORA - int(horas * H)


# (nombre, cambios, ultimo_aviso, corrida_anterior_ms, esperado)
CASOS = [
    ("Tranquilo", serie({12: 1.0, 6: 2.0, 1: 1.5, 0: 2.0}), None, hace(0.5), None),
    ("Cruza hacia arriba ahora", serie({12: 1.0, 6: 3.0, 1: 5.0, 0: 7.5}), None, hace(0.5), 1),
    ("Cruza hacia abajo ahora", serie({12: -1.0, 6: -4.0, 1: -6.0, 0: -7.3}), None, hace(0.5), -1),
    ("Ya estaba arriba en la corrida anterior", serie({12: 2.0, 3: 7.2, 1: 7.4, 0: 7.6}), None, hace(0.5), None),
    ("BUG: cron atrasado 4h, cruzó hace 3h -> nuevo", serie({12: 2.0, 3: 7.2, 1: 7.4, 0: 7.6}), None, hace(4), 1),
    ("Cron atrasado 4h, ya estaba arriba hace 5h", serie({12: 2.0, 5: 7.1, 3: 7.2, 0: 7.6}), None, hace(4), None),
    ("Ya avisado hace 30 min, mismo sentido", serie({12: 2.0, 2: 5.0, 0.5: 7.1, 0: 7.3}), {"ms": hace(0.5), "signo": 1}, hace(0.5), None),
    ("Avisado hace 13h: puede volver a avisar", serie({12.5: 2.0, 2: 5.0, 0: 7.3}), {"ms": hace(13), "signo": 1}, hace(0.5), 1),
    ("Avisó subida, ahora caída", serie({12: 0.0, 2: -5.0, 0: -7.5}), {"ms": hace(2), "signo": 1}, hace(0.5), -1),
    ("Superado hace 13h, fuera de la ventana", serie({13: 7.5, 6: 3.0, 0: 7.2}), None, hace(0.5), 1),
    ("Justo en el umbral cuenta", serie({6: 1.0, 0: 7.0}), None, hace(0.5), 1),
    ("Sin datos", [], None, hace(0.5), None),
    ("Sin corrida anterior conocida (API caída), sin aviso", serie({12: 2.0, 3: 7.2, 0: 7.6}), None, None, 1),
    ("Sin corrida anterior conocida, ya avisado", serie({12: 2.0, 3: 7.2, 0: 7.6}), {"ms": hace(3), "signo": 1}, None, None),
]


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    ok = 0
    for nombre, cambios, ultimo, anterior, esperado in CASOS:
        obtenido = decidir(cambios, UMBRAL, ultimo, AHORA, anterior)
        bien = obtenido == esperado
        ok += bien
        print(f"[{'OK ' if bien else 'MAL'}] {nombre:<54} esperado {esperado}  obtenido {obtenido}")
    print(f"\n{ok}/{len(CASOS)} casos OK")
    return ok == len(CASOS)


if __name__ == "__main__":
    sys.exit(0 if main() else 1)
