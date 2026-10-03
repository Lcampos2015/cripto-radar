"""Pruebas de V3-7: la regla de decision de evento.py (funcion pura, sin red)."""
import sys

from evento import decidir

H = 3600_000
AHORA = 1_000 * H
UMBRAL = 7.0


def serie(valores_por_hora_atras):
    """{horas_atras: pct} -> [(ms, pct)] ordenado, el de 0 horas atras es 'ahora'."""
    return sorted((AHORA - h * H, p) for h, p in valores_por_hora_atras.items())


# (nombre, cambios, ultimo_aviso, esperado)
CASOS = [
    ("Tranquilo", serie({12: 1.0, 6: 2.0, 1: 1.5, 0: 2.0}), None, None),
    ("Cruza hacia arriba ahora", serie({12: 1.0, 6: 3.0, 1: 5.0, 0: 7.5}), None, 1),
    ("Cruza hacia abajo ahora", serie({12: -1.0, 6: -4.0, 1: -6.0, 0: -7.3}), None, -1),
    ("Ya venía arriba hace 3h: no es nuevo", serie({12: 2.0, 3: 7.2, 1: 7.4, 0: 7.6}), None, None),
    ("Cruzó hace 30 min (cron atrasado): sigue siendo nuevo", serie({12: 2.0, 2: 5.0, 0.5: 7.1, 0: 7.3}), None, 1),
    ("Ya avisado hace 30 min, mismo sentido: no repetir", serie({12: 2.0, 2: 5.0, 0.5: 7.1, 0: 7.3}), {"ms": AHORA - H // 2, "signo": 1}, None),
    ("Avisado hace 13h: puede volver a avisar", serie({12.5: 2.0, 2: 5.0, 0: 7.3}), {"ms": AHORA - 13 * H, "signo": 1}, 1),
    ("Avisó subida, ahora caída: sí avisa", serie({12: 0.0, 2: -5.0, 0: -7.5}), {"ms": AHORA - 2 * H, "signo": 1}, -1),
    ("Superado hace 13h, fuera de la ventana: nuevo", serie({13: 7.5, 6: 3.0, 0: 7.2}), None, 1),
    ("Justo en el umbral cuenta", serie({6: 1.0, 0: 7.0}), None, 1),
    ("Sin datos", [], None, None),
]


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    ok = 0
    for nombre, cambios, ultimo, esperado in CASOS:
        obtenido = decidir(cambios, UMBRAL, ultimo, AHORA)
        bien = obtenido == esperado
        ok += bien
        print(f"[{'OK ' if bien else 'MAL'}] {nombre:<56} esperado {esperado}  obtenido {obtenido}")
    print(f"\n{ok}/{len(CASOS)} casos OK")
    return ok == len(CASOS)


if __name__ == "__main__":
    sys.exit(0 if main() else 1)
