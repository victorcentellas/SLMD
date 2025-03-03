#!/usr/bin/env python3

import paho.mqtt.client as mqtt
import time
import json
import uuid
from datetime import datetime

# Configuración del broker MQTT
BROKER = "localhost"
PORT = 1883
USERNAME = "user1"
PASSWORD = "clave123"

# Generar un ID único para cada agente
AGENT_ID = str(uuid.uuid4())

def get_mock_accelerometer():
    return {
        "x": round(-16 + (32 * (time.time() % 1)), 3),
        "y": round(-16 + (32 * ((time.time() + 1) % 1)), 3),
        "z": round(-16 + (32 * ((time.time() + 2) % 1)), 3)
    }

def get_mock_gyroscope():
    return {
        "x": round(-2000 + (4000 * (time.time() % 1)), 3),
        "y": round(-2000 + (4000 * ((time.time() + 1) % 1)), 3),
        "z": round(-2000 + (4000 * ((time.time() + 2) % 1)), 3)
    }

def get_mock_magnetometer():
    return {
        "x": round(-4900 + (9800 * (time.time() % 1)), 3),
        "y": round(-4900 + (9800 * ((time.time() + 1) % 1)), 3),
        "z": round(-4900 + (9800 * ((time.time() + 2) % 1)), 3)
    }

def get_mock_barometer():
    return round(260 + (1000 * (time.time() % 1)), 3)

def get_mock_gps():
    hora_mock = datetime.utcnow().strftime("%H%M%S")
    lat_mock = round(40.0 + (0.01 * (time.time() % 10)), 6)
    lon_mock = round(-3.0 + (0.01 * (time.time() % 10)), 6)
    return {"hora": hora_mock, "latitud": lat_mock, "longitud": lon_mock}



def publish_data(client, base_topic, data):
    """Publica cada valor en su subtopico correspondiente."""
    if isinstance(data, dict):
        for key, value in data.items():
            publish_data(client, f"{base_topic}/{key}", value)
    else:
        client.publish(base_topic, json.dumps(data))

def main():
    client = mqtt.Client()
    client.username_pw_set(USERNAME, PASSWORD)
    client.connect(BROKER, PORT, 60)
    client.loop_start()
    
    while True:
        sensores = {
            "acelerometro": get_mock_accelerometer(),
            "giroscopio": get_mock_gyroscope(),
            "magnetometro": get_mock_magnetometer(),
            "barometro": get_mock_barometer(),
            "gps": get_mock_gps()
        }
        
        base_topic = f"sensor/{AGENT_ID}"
        
        for sensor, data in sensores.items():
            publish_data(client, f"{base_topic}/{sensor}", data)
        
        print("Publicado en MQTT para el agente:", AGENT_ID)
        
        time.sleep(5)

if __name__ == "__main__":
    main()
