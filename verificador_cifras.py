"""Cripto Radar IA - V3-3: verificador de cifras (anti-alucinacion).

Revisa que cada numero y cada fecha del briefing exista en el JSON de datos
de V3-1. Si el LLM invento o calculo una cifra por su cuenta, el briefing sale
marcado con un aviso al principio y la lista de cifras dudosas.

Que acepta como valido:
- el valor tal cual, redondeado o recortado (84518 vale por 84518.01)
- decimales con coma o con punto, y separador de miles (84.518,01 / 84,518.01)
- el signo omitido ("cayo 0.43%" por -0.43)
- etiquetas pegadas a letras (el 20 de "EMA20", el 30 de "z30") y las
  constantes de referencia del glosario del prompt (PERMITIDOS)

Que NO atrapa: un numero correcto mal interpretado (ej. leer el MVRV sobre su
media como algo positivo). Eso depende del modelo elegido, no de este codigo.
"""
import re

# Periodos e umbrales que el prompt menciona y el LLM puede repetir sin que sean datos.
PERMITIDOS = {1, 2, 7, 14, 20, 25, 30, 50, 70, 75, 100, 200, 365}

FECHA_ISO = re.compile(r"\b\d{4}-\d{2}-\d{2}\b")
# No pegada a otro numero, pero si puede terminar una oracion ("del 05/10.")
FECHA_CORTA = re.compile(r"(?<!\d)(?<!\d[.,])\d{1,2}/\d{1,2}(?:/\d{2,4})?(?!\d)(?![.,]\d)")
# Numero suelto: no pegado a una letra por delante (EMA20) ni a otro numero; puede tener miles y decimales.
NUMERO = re.compile(r"(?<![A-Za-zÁÉÍÓÚáéíóúñÑ\d.,])[-+−]?\d+(?:[.,]\d+)*")

AVISO = "⚠️ VERIFICAR: estas cifras no están en los datos de hoy ({}). Puede ser un error del redactor."


def _valores(obj, out):
    """Todos los numeros del JSON (sin booleanos)."""
    if isinstance(obj, bool):
        return
    if isinstance(obj, (int, float)):
        out.append(abs(float(obj)))
    elif isinstance(obj, dict):
        for v in obj.values():
            _valores(v, out)
    elif isinstance(obj, list):
        for v in obj:
            _valores(v, out)


def _fechas(obj, out):
    """Fechas del JSON en los formatos que puede usar el LLM: 2026-10-02, 02/10, 2/10."""
    if isinstance(obj, str):
        for f in FECHA_ISO.findall(obj):
            a, m, d = f.split("-")
            out |= {f, f"{d}/{m}", f"{int(d)}/{int(m)}", f"{d}/{m}/{a}", f"{int(d)}/{int(m)}/{a}"}
    elif isinstance(obj, dict):
        for v in obj.values():
            _fechas(v, out)
    elif isinstance(obj, list):
        for v in obj:
            _fechas(v, out)


def _interpretaciones(token):
    """Lecturas posibles de un numero escrito: [(valor, decimales)]."""
    s = token.lstrip("+-−")
    lecturas = set()
    if "," in s and "." in s:
        dec = "," if s.rfind(",") > s.rfind(".") else "."
        mil = "." if dec == "," else ","
        lecturas.add(s.replace(mil, "").replace(dec, "."))
    elif "," in s or "." in s:
        sep = "," if "," in s else "."
        partes = s.split(sep)
        if len(partes) == 2:
            lecturas.add(partes[0] + "." + partes[1])          # decimal
        if all(len(p) == 3 for p in partes[1:]):
            lecturas.add("".join(partes))                      # separador de miles
    else:
        lecturas.add(s)
    return [(float(n), len(n.split(".")[1]) if "." in n else 0) for n in lecturas]


def _coincide(valor, decimales, valores):
    """El numero escrito es EXACTAMENTE algun valor del JSON redondeado o recortado a esos decimales.
    (Una tolerancia de +-1 en enteros dejaba pasar "10" por 9,28: redondeado es 9, no 10.)"""
    f = 10 ** decimales
    for v in valores:
        if abs(round(v, decimales) - valor) < 1e-9 or abs(int(v * f) / f - valor) < 1e-9:
            return True
    return False


def verificar(texto, datos):
    """Devuelve la lista de cifras y fechas del texto que no se pueden rastrear al JSON."""
    valores, fechas = [], set()
    _valores(datos, valores)
    _fechas(datos, fechas)

    dudosas = []
    resto = texto
    for patron in (FECHA_ISO, FECHA_CORTA):
        for f in patron.findall(resto):
            if f not in fechas:
                dudosas.append(f)
        resto = patron.sub(" ", resto)

    for token in NUMERO.findall(resto):
        lecturas = _interpretaciones(token)
        if any(d == 0 and v in PERMITIDOS for v, d in lecturas):
            continue
        if not any(_coincide(v, d, valores) for v, d in lecturas):
            dudosas.append(token)
    return dudosas


def anotar(texto, dudosas):
    """Si hay cifras dudosas, agrega el aviso al principio del briefing."""
    if not dudosas:
        return texto
    unicas = list(dict.fromkeys(dudosas))
    return AVISO.format(", ".join(unicas)) + "\n\n" + texto
