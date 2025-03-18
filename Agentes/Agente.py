#!/usr/bin/env python3

import paho.mqtt.client as mqtt
import time
import json
import uuid
from datetime import datetime
import threading
import random

# Configuración del broker MQTT
BROKER = "emqx"
PORT = 1883
USERNAME = "user1"
PASSWORD = "clave123"

AGENT_ID = str(uuid.uuid4())

# ======== SENSORES =========
def get_mock_accelerometer():
    return {
        "x": round(random.uniform(-15, 15), 3),  # ±15 m/s² -> aceleración en carrera/giro
        "y": round(random.uniform(-15, 15), 3),
        "z": round(random.uniform(-15, 15), 3)
    }

def get_mock_gyroscope():
    return {
        "x": round(random.uniform(-500, 500), 3),  # ±500°/s -> giros rápidos durante carrera
        "y": round(random.uniform(-500, 500), 3),
        "z": round(random.uniform(-500, 500), 3)
    }

def get_mock_magnetometer():
    return {
        "x": round(random.uniform(-50, 50), 3),  # ±50 µT -> variaciones naturales
        "y": round(random.uniform(-50, 50), 3),
        "z": round(random.uniform(-50, 50), 3)
    }

def get_mock_barometer():
    return {"presion": round(random.uniform(990, 1020), 2)}  # Presión atmosférica realista

def get_mock_gps():
    # Movimiento en el campo: variaciones pequeñas pero continuas
    return {
        "hora": datetime.utcnow().strftime("%H:%M:%S"),
        "latitud": round(40.0 + random.uniform(-0.0005, 0.0005), 6),  # Variación pequeña
        "longitud": round(-3.0 + random.uniform(-0.0005, 0.0005), 6)  # Variación pequeña
    }

# ======== PUBLICACIÓN =========
def publish_data(client, topic, data):
    """Publica el JSON en el tópico correspondiente."""
    client.publish(topic, json.dumps(data))

def publish_10DOF(client):
    while True:
        metricas_10DOF = {
            "id": AGENT_ID,
            "sensor": "10DOF",
            "data":{
            "acelerometro_x": get_mock_accelerometer()["x"],
            "acelerometro_y": get_mock_accelerometer()["y"],
            "acelerometro_z": get_mock_accelerometer()["z"],
            "giroscopio_x": get_mock_gyroscope()["x"],
            "giroscopio_y": get_mock_gyroscope()["y"],
            "giroscopio_z": get_mock_gyroscope()["z"],
            "magnetometro_x": get_mock_magnetometer()["x"],
            "magnetometro_y": get_mock_magnetometer()["y"],
            "magnetometro_z": get_mock_magnetometer()["z"],
            "presion": get_mock_barometer()["presion"]
            },
            "timestamp": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
            
        }
        
        base_topic = f"Si/{AGENT_ID}/10DOF"
        
        
        publish_data(client, base_topic, metricas_10DOF)
        
        time.sleep(0.1)  # 10 veces por segundo

def publish_GPS(client):
    while True:
        metricas_GPS =  {
            "id": AGENT_ID,
            "sensor": "GPS",
            "data":{
            "hora":get_mock_gps()["hora"],
            "latitud":get_mock_gps()["latitud"],
            "longitud": get_mock_gps()["longitud"],
            },
            "timestamp": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
        }
        base_topic = f"Si/{AGENT_ID}/GPS"
        publish_data(client, base_topic, metricas_GPS)
        
        time.sleep(0.2)  # 5 veces por segundo

# ======== MAIN =========
def main():
    client = mqtt.Client()
    client.username_pw_set(USERNAME, PASSWORD)
    client.connect(BROKER, PORT, 60)
    client.loop_start()
    
    thread_10DOF = threading.Thread(target=publish_10DOF, args=(client,), daemon=True)
    thread_GPS = threading.Thread(target=publish_GPS, args=(client,), daemon=True)
    
    thread_10DOF.start()
    thread_GPS.start()
    
    while True:
        time.sleep(1)

if __name__ == "__main__":
    main()
