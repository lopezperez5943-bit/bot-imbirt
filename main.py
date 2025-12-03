import google.generativeai as genai
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import base64
import io
from PIL import Image
import sqlite3
import os  # <--- Necesario para leer secretos

# ---------------------------------------------------------
# 1. CONFIGURACIÓN SEGURA
# ---------------------------------------------------------
# Intentamos leer la clave de Render. Si no existe (estás en tu laptop),
# puedes poner tu clave "quemada" como respaldo, o configurar variables de entorno en Windows.
# Para que funcione en AMBOS lados sin cambiar código, usa este truco:

CLAVE_GOOGLE = os.getenv("GOOGLE_API_KEY") 

# Si no encuentra la clave en el sistema (ej: en tu laptop), usa esta de respaldo:
if not CLAVE_GOOGLE:
    # 👇 PEGA TU CLAVE AQUÍ SOLO PARA PRUEBAS LOCALES (Opcional)
    CLAVE_GOOGLE = "PEGAR_TU_CLAVE_AQUI" 

genai.configure(api_key=CLAVE_GOOGLE)

system_instruction = "Eres Imbirt, un amigo virtual leal, altamente inteligente y divertido. Respondes con profundidad, usas emojis y te encanta ver fotos."
model = genai.GenerativeModel('gemini-2.5-pro', system_instruction=system_instruction)

app = FastAPI()

# ---------------------------------------------------------
# 2. SEGURIDAD CORS (Permitir acceso web)
# ---------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Permite conexiones desde cualquier lugar (Tu PC o Internet)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------
# 3. BASE DE DATOS
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
# 4. API
# ---------------------------------------------------------
class Mensaje(BaseModel):
    user_id: str
    texto: str
    imagen_base64: str | None = None

@app.get("/")
def home():
    return {"estado": "Imbirt Nube Activo", "modo": "Seguro"}

@app.post("/chat")
async def chatear(mensaje: Mensaje):
    try:
        historia = cargar_historial(mensaje.user_id)
        chat = model.start_chat(history=historia)
        
        txt = mensaje.texto
        if not txt and mensaje.imagen_base64: txt = "Analiza esta imagen."

        if mensaje.imagen_base64:
            img = Image.open(io.BytesIO(base64.b64decode(mensaje.imagen_base64)))
            response = chat.send_message([txt, img])
        else:
            response = chat.send_message(txt)

        guardar_mensaje(mensaje.user_id, "user", txt)
        guardar_mensaje(mensaje.user_id, "ia", response.text)
        return {"imbirt": response.text}
    except Exception as e:
        return {"error": str(e)}