"""Envía un aviso por Telegram con las tarjetas pendientes. Pensado para GitHub Actions."""
import os
import sys
import urllib.parse
import urllib.request

from basedatos import contar_pendientes

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
APP_URL = os.getenv("APP_URL", "")


def enviar(texto: str):
    datos = urllib.parse.urlencode({"chat_id": CHAT_ID, "text": texto}).encode()
    req = urllib.request.Request(f"https://api.telegram.org/bot{TOKEN}/sendMessage", data=datos)
    with urllib.request.urlopen(req, timeout=30) as r:
        if r.status != 200:
            raise RuntimeError(f"Telegram respondió {r.status}")


def main():
    if not TOKEN or not CHAT_ID:
        sys.exit("Faltan TELEGRAM_BOT_TOKEN o TELEGRAM_CHAT_ID")
    pend, total = contar_pendientes()
    if pend == 0:
        print("Sin pendientes: no se envía aviso.")
        return
    texto = f"🧠 Tienes {pend} tarjeta{'s' if pend != 1 else ''} pendiente{'s' if pend != 1 else ''} de repaso."
    if APP_URL:
        texto += f"\n{APP_URL}"
    enviar(texto)
    print(f"Aviso enviado ({pend} pendientes).")


if __name__ == "__main__":
    main()
