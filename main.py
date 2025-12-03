import google.generativeai as genai
from fastapi import FastAPI
from pydantic import BaseModel
import base64
import io
from PIL import Image
import sqlite3
from datetime import datetime

# ---------------------------------------------------------
# 1. CONFIGURACIÓN E IDENTIDAD
# ---------------------------------------------------------
# 👇 PEGA TU CLAVE DE GOOGLE AQUÍ
CLAVE_GOOGLE = "AIzaSyCUh_Ui6Hq73XHdqnV7OTM2vOVR6Rv_-xg" 
genai.configure(api_key=CLAVE_GOOGLE)

system_instruction = "Eres Imbirt, un amigo virtual leal y divertido. Recuerdas lo que hablamos en el pasado. Puedes ver fotos y opinar sobre ellas."
model = genai.GenerativeModel('gemini-2.0-flash', system_instruction=system_instruction)

app = FastAPI()

# ---------------------------------------------------------
# 2. GESTIÓN DE BASE DE DATOS (SQLITE)
# ---------------------------------------------------------
DB_NAME = "memoria_imbirt.db"

def init_db():
    """Crea la tabla si no existe (se ejecuta al iniciar)"""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS historial (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT,
            role TEXT,
            content TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

def guardar_mensaje(user_id, role, content):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO historial (user_id, role, content) VALUES (?, ?, ?)", 
                   (str(user_id), role, content))
    conn.commit()
    conn.close()

def cargar_historial(user_id):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    # Recuperamos los últimos 10 mensajes para dar contexto
    cursor.execute("SELECT role, content FROM historial WHERE user_id = ? ORDER BY id ASC LIMIT 20", (str(user_id),))
    rows = cursor.fetchall()
    conn.close()
    
    historial_gemini = []
    for role, content in rows:
        gemini_role = "model" if role == "ia" else "user"
        historial_gemini.append({"role": gemini_role, "parts": [content]})
    
    return historial_gemini

init_db()

# ---------------------------------------------------------
# 3. API (ENDPOINTS)
# ---------------------------------------------------------
class Mensaje(BaseModel):
    user_id: str
    texto: str
    imagen_base64: str | None = None

@app.post("/chat")
async def chatear(mensaje: Mensaje):
    try:
        # 1. Cargamos memoria
        historia_previa = cargar_historial(mensaje.user_id)
        chat_session = model.start_chat(history=historia_previa)
        
        # 2. Preparamos el mensaje actual
        texto_usuario = mensaje.texto
        if not texto_usuario and mensaje.imagen_base64:
            texto_usuario = "Analiza esta imagen detalladamente."

        # 3. Enviamos a Gemini (Con o sin foto)
        if mensaje.imagen_base64:
            imagen_bytes = base64.b64decode(mensaje.imagen_base64)
            imagen = Image.open(io.BytesIO(imagen_bytes))
            response = chat_session.send_message([texto_usuario, imagen])
        else:
            response = chat_session.send_message(texto_usuario)

        texto_respuesta = response.text

        # 4. Guardamos en la base de datos
        guardar_mensaje(mensaje.user_id, "user", texto_usuario)
        guardar_mensaje(mensaje.user_id, "ia", texto_respuesta)

        return {"imbirt": texto_respuesta}
        
    except Exception as e:
        return {"error": f"Error en main.py: {str(e)}"}