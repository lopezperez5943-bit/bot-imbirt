import ollama
import time

# Configuración del sistema (La personalidad)
SYSTEM_PROMPT = """
Eres Imbirt, una inteligencia artificial soberana y autónoma. 
No dependes de la nube. Vives en el hardware local del usuario.
Eres sarcástico, técnico y te sientes orgulloso de correr en silicio local.
"""

def pensar_localmente(mensaje_usuario):
    print("🧠 (Procesando en CPU local... sin enviar datos a Google)...")
    
    inicio = time.time()
    
    # Aquí ocurre la magia. No hay API Key. No hay internet.
    # Usamos 'llama3.2' que es el modelo que descargaste en la terminal negra
    respuesta = ollama.chat(model='llama3.2', messages=[
        {'role': 'system', 'content': SYSTEM_PROMPT},
        {'role': 'user', 'content': mensaje_usuario},
    ])
    
    fin = time.time()
    tiempo_total = fin - inicio
    
    print(f"⚡ Pensado en {tiempo_total:.2f} segundos.")
    return respuesta['message']['content']

# Bucle de chat en la terminal
if __name__ == "__main__":
    print("--- 🛡️ MODO LOCAL ACTIVADO: Llama 3.2 🛡️ ---")
    print("Escribe 'salir' para terminar.\n")
    
    while True:
        # Input del usuario
        usuario = input("Tú: ")
        if usuario.lower() == "salir":
            break
            
        # Llamada a la IA local
        try:
            respuesta_ia = pensar_localmente(usuario)
            print(f"Imbirt (Local): {respuesta_ia}\n")
        except Exception as e:
            print(f"❌ Error: {e}")
            print("Asegúrate de que Ollama esté instalado y corriendo.")