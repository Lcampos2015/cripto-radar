"""Cripto Radar IA - V3-4: briefing diario completo.

datos duros (V3-1) -> redaccion del LLM (V3-2) -> verificador de cifras (V3-3) -> Telegram.

Lo corre GitHub Actions todos los dias a las 19:05 de Peru (workflow briefing.yml).
Si el LLM falla, igual manda un aviso con los datos crudos, asi Lucho se entera
en vez de recibir silencio. Solo informa: NUNCA ejecuta compra/venta (regla dura W1).
"""
import os
import sys

import briefing_datos
import briefing_llm
import notify
import verificador_cifras
import watchlist_analyst


def cabecera(datos):
    fecha = next((m.get("fecha_vela") for m in datos["monedas"].values() if m.get("fecha_vela")), "?")
    return f"🧠 BRIEFING DIARIO · vela del {fecha}"


def crudo(datos):
    """Respaldo si el LLM no responde: solo los numeros, sin redaccion."""
    lineas = []
    for nombre, m in datos["monedas"].items():
        if m:
            lineas.append(f"{nombre} {m.get('cierre')} | 1d {m.get('cambio_1d_pct')}% | 7d {m.get('cambio_7d_pct')}% | "
                          f"RSI {m.get('rsi14')} | sobre EMA200: {m.get('sobre_ema200')}")
    mc = datos.get("miedo_codicia") or {}
    lineas.append(f"Miedo/codicia: {mc.get('valor', 'sin datos')}")
    return "\n".join(lineas)


def watchlist():
    """Informe de la watchlist completa (BTC, ETH, WLD, NEAR, XRP), numeros crudos sin LLM.
    Antes llegaba cada 30 min con el monitor; desde el 2026-10-03 llega una vez por dia aca."""
    try:
        return watchlist_analyst.build_report()
    except Exception as e:
        return f"📊 Watchlist: sin datos hoy ({type(e).__name__})"


def armar(datos=None, titulo=None):
    """Devuelve (mensaje, resumen_para_el_log). evento.py lo reusa con su propio titulo y datos."""
    datos = datos or briefing_datos.recolectar()
    titulo = titulo or cabecera(datos)
    try:
        texto, info = briefing_llm.redactar(datos)
    except Exception as e:
        aviso = f"⚠️ Hoy no se pudo redactar el briefing ({type(e).__name__}). Datos crudos:"
        mensaje = f"{titulo}\n\n{aviso}\n{crudo(datos)}\n\n{watchlist()}"
        return mensaje, {"error_llm": str(e)[:200], "faltantes": datos["faltantes"]}

    cuerpo = texto.replace(briefing_llm.PIE, "").strip()
    dudosas = verificador_cifras.verificar(cuerpo, datos)   # solo se verifica lo que redacto el LLM
    info.update({"dudosas": dudosas, "faltantes": datos["faltantes"]})
    mensaje = f"{titulo}\n\n{verificador_cifras.anotar(cuerpo, dudosas)}\n\n{watchlist()}\n\n{briefing_llm.PIE}"
    return mensaje, info


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    mensaje, info = armar()
    print(mensaje)
    print("\n--- log ---")
    print(info)
    enviado = notify.send_telegram(mensaje)
    print("Enviado:", enviado)
    if os.environ.get("GITHUB_ACTIONS") == "true":
        # Resumen tecnico como anotacion del run: se lee por la API publica sin sesion (sin secretos)
        print(f"::notice title=briefing::enviado={enviado} {info}")


if __name__ == "__main__":
    main()
