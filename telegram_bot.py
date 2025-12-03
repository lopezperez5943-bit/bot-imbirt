import logging
import requests
import base64
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters

# ---------------------------------------------------------
# CONFIGURACIÓN
# ---------------------------------------------------------
# 👇 PEGA TU TOKEN DE TELEGRAM AQUÍ (Dentro de las comillas)
TELEGRAM_TOKEN = "8546282659:AAGdLIJsXcnWjAydYdxGqwhppmXBgY8Hd1o" 
API_CEREBRO = "http://127.0.0.1:8000/chat" 

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_name = update.effective_user.first_name
    await update.message.reply_text(f"¡Hola {user_name}! Soy Imbirt. Tengo ojos 👁️ y memoria 🧠. Mándame una foto o cuéntame algo.")

async def procesar_mensaje(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # 1. Identificamos al usuario (Para la Base de Datos)
    user_id = str(update.effective_user.id)
    mensaje_texto = update.message.text
    imagen_b64 = None
    
    # 2. DETECTAR SI HAY FOTO
    if update.message.photo:
        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action='upload_photo')
        
        # Descargar foto de los servidores de Telegram
        foto_file = await update.message.photo[-1].get_file()
        archivo_foto = await foto_file.download_as_bytearray()
        
        # Convertir a Base64 para poder enviarla a tu API
        imagen_b64 = base64.b64encode(archivo_foto).decode('utf-8')
        
        # Si la foto tiene texto abajo (caption), lo usamos
        mensaje_texto = update.message.caption if update.message.caption else ""
    else:
        # Si es solo texto
        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action='typing')

    # 3. ENVIAR AL CEREBRO (main.py)
    try:
        payload = {
            "user_id": user_id,
            "texto": mensaje_texto if mensaje_texto else "",
            "imagen_base64": imagen_b64
        }
        
        # Enviamos la petición POST a tu cerebro local
        respuesta = requests.post(API_CEREBRO, json=payload)
        
        if respuesta.status_code == 200:
            texto_ia = respuesta.json().get("imbirt", "...")
            await update.message.reply_text(texto_ia)
        else:
            await update.message.reply_text(f"🥴 Error del servidor: {respuesta.status_code}")

    except Exception as e:
        await update.message.reply_text(f"🔌 No conecto con main.py. ¿Está encendido? Error: {e}")

if __name__ == '__main__':
    application = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    
    # Manejador HÍBRIDO: Escucha Texto O (pipe |) Fotos
    manejador = MessageHandler(filters.TEXT | filters.PHOTO, procesar_mensaje)
    
    application.add_handler(CommandHandler('start', start))
    application.add_handler(manejador)

    print("🤖 Imbirt V3 (Ojos + Memoria) ESCUCHANDO...")
    application.run_polling()