import google.generativeai as genai
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import base64
import io
from PIL import Image
import sqlite3
import os
import edge_tts # <--- La librería de voz natural
import tempfile

# ---------------------------------------------------------
# 1. CONFIGURACIÓN
# ---------------------------------------------------------
# Intentamos leer la clave de Render. Si no existe, usa la de respaldo.
CLAVE_GOOGLE = os.getenv("GOOGLE_API_KEY") 
if not CLAVE_GOOGLE:
    CLAVE_GOOGLE = "PEGAR_TU_CLAVE_AQUI" 

genai.configure(api_key=CLAVE_GOOGLE)

# Instrucción para que las respuestas sean ideales para hablar
system_instruction = "Eres Imbirt, un asistente de IA avanzado. Tus respuestas son concisas, naturales y conversacionales, perfectas para ser leídas en voz alta. Usas emojis ocasionalmente."
model = genai.GenerativeModel('gemini-2.5-pro', system_instruction=system_instruction)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------
# 2. BASE DE DATOS
# ---------------------------------------------------------
DB_NAME = "memoria_imbirt.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS historial (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT, role TEXT, content TEXT, timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

def guardar_mensaje(user_id, role, content):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO historial (user_id, role, content) VALUES (?, ?, ?)", (str(user_id), role, content))
    conn.commit()
    conn.close()

def cargar_historial(user_id):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT role, content FROM historial WHERE user_id = ? ORDER BY id ASC LIMIT 20", (str(user_id),))
    rows = cursor.fetchall()
    conn.close()
    historial = []
    for role, content in rows:
        g_role = "model" if role == "ia" else "user"
        historial.append({"role": g_role, "parts": [{"text": content}]})
    return historial

init_db()

# ---------------------------------------------------------
# 3. FUNCIÓN DE VOZ NEURAL
# ---------------------------------------------------------
async def generar_audio_neural(texto):
    # Voces disponibles: 
    # 'es-MX-DaliaNeural' (Mujer México)
    # 'es-MX-JorgeNeural' (Hombre México)
    # 'es-ES-AlvaroNeural' (Hombre España)
    VOZ = "es-MX-DaliaNeural" 
    
    communicate = edge_tts.Communicate(texto, VOZ)
    
    # Guardamos en memoria RAM para velocidad
    audio_stream = io.BytesIO()
    async for chunk in communicate.stream():
        if chunk["type"] == "audio":
            audio_stream.write(chunk["data"])
            
    audio_stream.seek(0)
    # Convertimos a base64 para enviarlo a la web
    audio_base64 = base64.b64encode(audio_stream.read()).decode('utf-8')
    return audio_base64

# ---------------------------------------------------------
# 4. API
# ---------------------------------------------------------
class Mensaje(BaseModel):
    user_id: str
    texto: str
    imagen_base64: str | None = None
    usar_voz: bool = False # Nuevo campo: ¿Quiere audio?

@app.get("/")
def home():
    return {"estado": "Imbirt Voz Neural Online"}

@app.post("/chat")
async def chatear(mensaje: Mensaje):
    try:
        historia = cargar_historial(mensaje.user_id)
        chat = model.start_chat(history=historia)
        
        txt = mensaje.texto
        if not txt and mensaje.imagen_base64: txt = "Describe lo que ves."

        # Generar respuesta de texto con IA
        if mensaje.imagen_base64:
            img = Image.open(io.BytesIO(base64.b64decode(mensaje.imagen_base64)))
            response = chat.send_message([txt, img])
        else:
            response = chat.send_message(txt)

        texto_respuesta = response.text
        
        # Guardar en memoria
        guardar_mensaje(mensaje.user_id, "user", txt)
        guardar_mensaje(mensaje.user_id, "ia", texto_respuesta)

        # Generar Audio si se solicita
        audio_data = None
        if mensaje.usar_voz:
            # Limpiamos asteriscos (*) para que no lea "asterisco hola asterisco"
            texto_limpio = texto_respuesta.replace("*", "").replace("#", "")
            audio_data = await generar_audio_neural(texto_limpio)

        return {
            "imbirt": texto_respuesta,
            "audio": audio_data # Aquí va el archivo de sonido
        }
        
    except Exception as e:
        return {"error": str(e)}