# Modifica tus imports arriba del todo
import sqlite3
import requests
import time
from datetime import datetime
from zoneinfo import ZoneInfo # <- Añade esto
import os

DB_PATH = "/usb/agenda/instance/agenda.db"
NTFY_URL = "https://ntfy.sh/mi_agenda_raspi"
LOG_PATH = "/usb/agenda/cron_debug.log"

# Define la zona horaria local
ZONA_LOCAL = ZoneInfo("Europe/Madrid")

def log_message(msg):
    with open(LOG_PATH, "a") as f:
        # Usamos la zona horaria local también para el log
        f.write(f"[{datetime.now(ZONA_LOCAL).strftime('%Y-%m-%d %H:%M:%S')}] {msg}\n")

log_message("⏳ Demonio cron.py con Zona Horaria activa...")

while True:
    try:
        if not os.path.exists(DB_PATH):
            time.sleep(10)
            continue

        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute("SELECT id, titulo, fecha_hora, mensaje FROM evento")
        eventos = cursor.fetchall()
        
        # 🌟 OBTENEMOS LA HORA REAL DE TU PAÍS, NO LA DEL SISTEMA
        ahora = datetime.now(ZONA_LOCAL)
        
        for id_evento, titulo, fecha_hora_str, mensaje in eventos:
            fecha_hora_str = fecha_hora_str.replace('T', ' ')
            try:
                # Convertimos el texto y le asignamos la misma zona horaria para comparar manzanas con manzanas
                fecha_evento = datetime.strptime(fecha_hora_str, "%Y-%m-%d %H:%M").replace(tzinfo=ZONA_LOCAL)
            except ValueError:
                fecha_evento = datetime.strptime(fecha_hora_str, "%Y-%m-%d %H:%M:%S").replace(tzinfo=ZONA_LOCAL)

            # Si la hora actual de Madrid ya alcanzó o superó la del evento, se dispara
            if ahora >= fecha_evento:
                log_message(f"🚀 Disparando alerta horaria: {titulo}")
                
                res = requests.post(
                    NTFY_URL, 
                    data=mensaje.encode('utf-8'), 
                    headers={"Title": titulo, 
			"Priority": "high", 
			"Tags": "calendar",
                )
                
                if res.status_code == 200:
                    log_message(f"✅ Notificación enviada con éxito")
                    cursor.execute("DELETE FROM evento WHERE id = ?", (id_evento,))
                    
        conn.commit()
        conn.close()
        
    except Exception as e:
        log_message(f"💥 Error: {e}")
        
    time.sleep(15)
