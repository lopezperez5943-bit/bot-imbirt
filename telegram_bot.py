import logging
import requests
import base64
import os
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters

# ---------------------------------------------------------
# CONFIGURACIÓN
# ---------------------------------------------------------
# 👇 PEGA TU TOKEN DE TELEGRAM AQUÍ
TELEGRAM_TOKEN = "8546282659:AAGdLIJsXcnWjAydYdxGqwhppmXBgY8Hd1o" 

# --- CORRECCIÓN CLAVE PARA LA NUBE ---
# Leemos el puerto que Render nos asignó. Si no hay (estamos en local), usa 8000.
PORT = os.getenv("PORT", "8000")
API_CEREBRO = f"http://127.0.0.1:{PORT}/chat"

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_name = update.effective_user.first_name
    await update.message.reply_text(f"¡Hola {user_name}! Soy Imbirt Cloud ☁️. Estoy vivo en el puerto {PORT}.")

async def procesar_mensaje(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    mensaje_texto = update.message.text
    imagen_b64 = None
    
    if update.message.photo:
        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action='upload_photo')
        foto_file = await update.message.photo[-1].get_file()
        archivo_foto = await foto_file.download_as_bytearray()
        imagen_b64 = base64.b64encode(archivo_foto).decode('utf-8')
        mensaje_texto = update.message.caption if update.message.caption else ""
    else:
        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action='typing')

    try:
        payload = {
            "user_id": user_id,
            "texto": mensaje_texto if mensaje_texto else "",
            "imagen_base64": imagen_b64
        }
        
        # Enviamos al cerebro en el puerto dinámico
        respuesta = requests.post(API_CEREBRO, json=payload)
        
        if respuesta.status_code == 200:
            texto_ia = respuesta.json().get("imbirt", "...")
            await update.message.reply_text(texto_ia)
        else:
            await update.message.reply_text(f"🥴 Error {respuesta.status_code}: Cerebro mareado.")

    except Exception as e:
        # Este mensaje te ayuda a saber qué puerto está intentando usar
        await update.message.reply_text(f"🔌 Error conectando a {API_CEREBRO}: {e}")

if __name__ == '__main__':
    application = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    manejador = MessageHandler(filters.TEXT | filters.PHOTO, procesar_mensaje)
    application.add_handler(CommandHandler('start', start))
    application.add_handler(manejador)
    print(f"🤖 ¡IMBIRT CLOUD V4 ACTUALIZADO! Puerto: {PORT}")
    application.run_polling()