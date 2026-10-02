"""Cripto Radar IA - M5: notificaciones por Telegram.

Modulo compartido: envia un mensaje al chat de Lucho via el bot.
Solo envia alertas informativas. NUNCA ejecuta operaciones (regla dura W1).

Credenciales, en orden de prioridad:
  1. Variables de entorno TELEGRAM_TOKEN / TELEGRAM_CHAT_ID  (GitHub Actions)
  2. config.json local, que esta en .gitignore                (tu PC)
"""
import json
import os
import requests

HERE = os.path.dirname(os.path.abspath(__file__))
CONFIG = os.path.join(HERE, "config.json")
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) CriptoRadar/0.1"}

# Telegram corta los mensajes a 4096 caracteres
MAX_LEN = 4000


def load_config():
    """Devuelve {token, chat_id}. Entorno primero, config.json de respaldo."""
    token = os.environ.get("TELEGRAM_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    if token and chat_id:
        return {"telegram_token": token, "telegram_chat_id": chat_id}

    if not os.path.exists(CONFIG):
        raise RuntimeError(
            "Faltan credenciales: defini TELEGRAM_TOKEN y TELEGRAM_CHAT_ID "
            "como variables de entorno, o crea config.json local."
        )
    with open(CONFIG, "r", encoding="utf-8") as f:
        return json.load(f)


def _split(text, limit=MAX_LEN):
    """Parte un texto largo en trozos respetando los saltos de linea."""
    if len(text) <= limit:
        return [text]
    partes, actual = [], ""
    for linea in text.split("\n"):
        if len(actual) + len(linea) + 1 > limit:
            partes.append(actual.rstrip())
            actual = ""
        actual += linea + "\n"
    if actual.strip():
        partes.append(actual.rstrip())
    return partes


def send_telegram(text):
    """Envia un mensaje (lo parte si es largo). Devuelve True si todo salio ok."""
    cfg = load_config()
    url = f"https://api.telegram.org/bot{cfg['telegram_token']}/sendMessage"
    ok = True
    for parte in _split(text):
        r = requests.post(
            url,
            json={"chat_id": cfg["telegram_chat_id"], "text": parte},
            headers=HEADERS,
            timeout=20,
        )
        r.raise_for_status()
        ok = ok and r.json()["ok"]
    return ok


if __name__ == "__main__":
    print("Enviado:", send_telegram("notify.py configurado correctamente (M5)."))
