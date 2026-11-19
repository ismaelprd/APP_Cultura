"""Bot de Telegram para repasar tus tarjetas desde el móvil.

Ejecútalo en un equipo que esté encendido mientras lo uses:  python bot.py
Solo responde al chat indicado en TELEGRAM_CHAT_ID.
"""
import json
import logging
import os

from fsrs import Rating
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Application, CallbackQueryHandler, CommandHandler, ContextTypes

import basedatos as db

logging.basicConfig(level=logging.WARNING)
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")


def autorizado(update: Update) -> bool:
    chat = update.effective_chat
    return bool(CHAT_ID) and chat is not None and str(chat.id) == str(CHAT_ID)


async def enviar_pregunta(bot, chat_id, card):
    texto = f"{card['area']} · {card['tema']}\n\n{card['pregunta']}"
    if card["tipo"] == "ordenar":
        texto += "\n\nOrdena: " + " · ".join(json.loads(card["elementos"]))
    teclado = InlineKeyboardMarkup(
        [[InlineKeyboardButton("Mostrar respuesta", callback_data=f"show:{card['id']}")]])
    await bot.send_message(chat_id, texto, reply_markup=teclado)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not CHAT_ID:
        await update.message.reply_text(
            f"Tu chat id es: {update.effective_chat.id}\n"
            "Guárdalo en la variable TELEGRAM_CHAT_ID y reinicia el bot.")
        return
    if not autorizado(update):
        await update.message.reply_text("No autorizado.")
        return
    await update.message.reply_text("Hola 🧠\n/repasar - empezar a repasar\n/pendientes - cuántas tienes")


async def pendientes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not autorizado(update):
        return
    pend, total = db.contar_pendientes()
    await update.message.reply_text(f"Pendientes: {pend} · Totales: {total}")


async def repasar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not autorizado(update):
        return
    card = db.siguiente_tarjeta()
    if card is None:
        await update.message.reply_text("🎉 No tienes repasos pendientes.")
        return
    await enviar_pregunta(context.bot, update.effective_chat.id, card)


async def boton(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    if not autorizado(update):
        await q.answer("No autorizado", show_alert=True)
        return
    await q.answer()
    accion, *resto = q.data.split(":")
    if accion == "show":
        filas = db.consultar("SELECT * FROM cards WHERE id=?", (int(resto[0]),), cols=db.CARD_COLS)
        if not filas:
            await q.edit_message_text("Esa tarjeta ya no existe.")
            return
        c = filas[0]
        texto = f"{c['pregunta']}\n\n✅ {c['respuesta']}\n\n{c['explicacion']}"
        if c.get("mnemotecnia"):
            texto += f"\n\n💡 {c['mnemotecnia']}"
        i = c["id"]
        teclado = InlineKeyboardMarkup([[
            InlineKeyboardButton("Otra vez", callback_data=f"rate:{i}:1"),
            InlineKeyboardButton("Difícil", callback_data=f"rate:{i}:2"),
            InlineKeyboardButton("Bien", callback_data=f"rate:{i}:3"),
            InlineKeyboardButton("Fácil", callback_data=f"rate:{i}:4"),
        ]])
        await q.edit_message_text(texto, reply_markup=teclado)
    elif accion == "rate":
        db.repasar(int(resto[0]), Rating(int(resto[1])))
        await q.edit_message_reply_markup(reply_markup=None)
        card = db.siguiente_tarjeta()
        chat_id = update.effective_chat.id
        if card is None:
            await context.bot.send_message(chat_id, "🎉 No quedan repasos pendientes.")
        else:
            await enviar_pregunta(context.bot, chat_id, card)


def main():
    if not TOKEN:
        raise SystemExit("Falta TELEGRAM_BOT_TOKEN")
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("pendientes", pendientes))
    app.add_handler(CommandHandler("repasar", repasar))
    app.add_handler(CallbackQueryHandler(boton))
    print("Bot en marcha. Pulsa Ctrl+C para parar.")
    app.run_polling()


if __name__ == "__main__":
    main()
