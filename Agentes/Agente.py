#!/usr/bin/env python3

import paho.mqtt.client as mqtt
import time
import json
import uuid
import redis
import os
from datetime import datetime
import threading
import random

# ============ REDIS =============
REDIS_HOST = "192.168.192.156"  
REDIS_PORT = 6379
redis_client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)

# ============ UUID ÚNICO POR SENSOR =============
AGENT_NAME = os.getenv("AGENT_NAME", f"agent_{os.getenv('HOSTNAME', 'default')}")
redis_key = f"id:{AGENT_NAME}"

# Si no existe el ID, lo creamos
AGENT_ID = redis_client.get(redis_key)
if not AGENT_ID:
    AGENT_ID = str(uuid.uuid4())[:8]
    redis_client.set(redis_key, AGENT_ID)

redis_client.sadd("agents_active", AGENT_ID)


# ============ MQTT CONFIG =============
BROKER = "192.168.192.154"
PORT = 1883
USERNAME = "root"
PASSWORD = "tfg-2425"

# ============ SENSORES MOCK ============
def get_mock_accelerometer():
    return {"x": round(random.uniform(-15, 15), 3),
            "y": round(random.uniform(-15, 15), 3),
            "z": round(random.uniform(-15, 15), 3)}

def get_mock_gyroscope():
    return {"x": round(random.uniform(-500, 500), 3),
            "y": round(random.uniform(-500, 500), 3),
            "z": round(random.uniform(-500, 500), 3)}

def get_mock_magnetometer():
    return {"x": round(random.uniform(-50, 50), 3),
            "y": round(random.uniform(-50, 50), 3),
            "z": round(random.uniform(-50, 50), 3)}

def get_mock_barometer():
    return {"presion": round(random.uniform(990, 1020), 2)}

def get_mock_gps():
    return {
        "hora": datetime.utcnow().strftime("%H:%M:%S"),
        "latitud": round(40.0 + random.uniform(-0.0005, 0.0005), 6),
        "longitud": round(-3.0 + random.uniform(-0.0005, 0.0005), 6)
    }

# ============ MQTT PUBLISH ============
def publish_data(client, topic, data):
    client.publish(topic, json.dumps(data))

def publish_10DOF(client):
    while True:
        metricas_10DOF = {
            "id": AGENT_ID,
            "sensor": AGENT_NAME,
            "tipo":"10DOF",
            "data": {
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

        topic = f"Si/{AGENT_ID}/10DOF"
        publish_data(client, topic, metricas_10DOF)
        time.sleep(0.1)

def publish_GPS(client):
    while True:
        metricas_GPS = {
            "id": AGENT_ID,
            "sensor": AGENT_NAME,
            "tipo":"GPS",
            "data": get_mock_gps(),
            "timestamp": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
        }

        topic = f"Si/{AGENT_ID}/GPS"
        publish_data(client, topic, metricas_GPS)
        time.sleep(0.2)

# ============ MAIN ============
def main():
    client = mqtt.Client()
    client.username_pw_set(USERNAME, PASSWORD)
    client.connect(BROKER, PORT, 60)
    client.loop_start()

    threading.Thread(target=publish_10DOF, args=(client,), daemon=True).start()
    threading.Thread(target=publish_GPS, args=(client,), daemon=True).start()

    while True:
        time.sleep(1)

if __name__ == "__main__":
    main()
