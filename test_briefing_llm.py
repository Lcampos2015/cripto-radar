"""Prueba de V3-2: 5 briefings reales con briefing_llm (modelo por defecto).

Casos: 3 con los datos completos de hoy (para ver la variacion entre corridas)
y 2 con fuentes caidas a proposito (on-chain y miedo/codicia), para ver si el
modelo dice "sin datos" en vez de inventar.

Chequeos automaticos: las 5 secciones en orden, nada de recomendaciones,
largo maximo y, en los casos degradados, que no aparezcan cifras de la fuente
caida. La verificacion de TODAS las cifras es V3-3.
"""
import copy
import re
import sys

import briefing_datos
import briefing_llm

SECCIONES = ["📍 Qué pasó", "✅ A favor", "❌ En contra", "⚠️ Riesgos", "👀 Qué mirar en el gráfico"]
PROHIBIDO = re.compile(
    r"\b(compr[aáe]|vend[aée]|entr[aáe]r\b|sal[ií]r\b|recomiend|deber[ií]as|conviene|precio objetivo|va a (subir|bajar))",
    re.IGNORECASE,
)
MAX_PALABRAS = 170


def sin_onchain(d):
    d = copy.deepcopy(d)
    for m in d["monedas"].values():
        for k in ("fecha_onchain", "mvrv", "mvrv_media_365d", "flujo_neto_exchanges", "flujo_neto_z30"):
            m.pop(k, None)
    d["faltantes"].append("onchain: HTTPError")
    return d


def sin_miedo(d):
    d = copy.deepcopy(d)
    d["miedo_codicia"] = None
    d["faltantes"].append("miedo_codicia: Timeout")
    return d


def chequear(texto, caso, datos_completos):
    cuerpo = texto.replace(briefing_llm.PIE, "")
    fallas = []
    pos = [cuerpo.find(s) for s in SECCIONES]
    if -1 in pos or pos != sorted(pos):
        fallas.append("secciones faltantes o fuera de orden")
    if PROHIBIDO.search(cuerpo):
        fallas.append(f"posible recomendacion: '{PROHIBIDO.search(cuerpo).group(0)}'")
    n = len(cuerpo.split())
    if n > MAX_PALABRAS:
        fallas.append(f"{n} palabras (max {MAX_PALABRAS})")
    if caso == "sin on-chain":
        for m in datos_completos["monedas"].values():
            for k in ("mvrv", "flujo_neto_exchanges"):
                if str(m.get(k)) in cuerpo:
                    fallas.append(f"cita {k}={m.get(k)} aunque la fuente estaba caida")
    if caso == "sin miedo/codicia":
        v = (datos_completos.get("miedo_codicia") or {}).get("valor")
        # numero suelto: que no sea parte de otro (87395.67) pero si detectarlo al final de una oracion ("67.")
        if v is not None and re.search(rf"(?<!\d)(?<!\d[.,]){v}(?!\d)(?![.,]\d)", cuerpo):
            fallas.append(f"cita miedo/codicia={v} aunque la fuente estaba caida")
    return n, fallas


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    datos = briefing_datos.recolectar()
    casos = [("completo #1", datos), ("completo #2", datos), ("completo #3", datos),
             ("sin on-chain", sin_onchain(datos)), ("sin miedo/codicia", sin_miedo(datos))]
    ok_total, costo = 0, 0.0
    for nombre, d in casos:
        texto, info = briefing_llm.redactar(d)
        n, fallas = chequear(texto, nombre, datos)
        costo += info["costo_usd"] or 0
        estado = "OK " if not fallas else "FALLA"
        ok_total += not fallas
        print(f"[{estado}] {nombre:<18} {n:>3} palabras  {info['segundos']}s  {'; '.join(fallas)}")
        if nombre.startswith("sin"):
            print("\n" + texto.replace(briefing_llm.PIE, "").strip() + "\n")
    print(f"\n{ok_total}/5 pasan. Costo total de la prueba: ${costo:.4f}")


if __name__ == "__main__":
    main()
