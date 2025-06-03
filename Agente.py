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
import math

# ============ REDIS =============
REDIS_HOST = "192.168.192.156"  
REDIS_PORT = 6379
redis_client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)

# ============ UUID ÚNICO POR SENSOR =============
AGENT_NAME = os.getenv("AGENT_NAME", f"agent_{os.getenv('HOSTNAME', 'default')}")
env_agent_id = os.getenv("AGENT_ID", str(uuid.uuid4())[:8])
redis_key = f"id:{AGENT_NAME}"

db_agent_id = redis_client.get(redis_key)
if db_agent_id is not None:
    AGENT_ID = db_agent_id
else:
    AGENT_ID = env_agent_id
    redis_client.set(redis_key, AGENT_ID)

redis_client.sadd("agents_active", AGENT_ID)

# ============ MQTT CONFIG ============
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
        "latitud": round(40.0 + random.uniform(-0.0005, 0.0005), 6),
        "longitud": round(-3.0 + random.uniform(-0.0005, 0.0005), 6),
        "altitud": round(random.uniform(0, 100), 2),
        "speed": round(random.uniform(0, 120), 2),
        "satellites": random.randint(4, 12),
        "hdop": round(random.uniform(0.5, 3.0), 2),
        "hora": datetime.utcnow().strftime("%H:%M:%S")
    }

def get_mock_environment():
    return {
        "temp": round(random.uniform(20, 30), 2),
        "humidity": round(random.uniform(30, 70), 2),
        "pressure": get_mock_barometer()["presion"]
    }

def get_mock_quaternion():
    # Generamos valores aleatorios y normalizamos
    w = random.uniform(0, 1)
    x = random.uniform(0, 1)
    y = random.uniform(0, 1)
    z = random.uniform(0, 1)
    norm = math.sqrt(w*w + x*x + y*y + z*z)
    return {"w": round(w/norm, 3),
            "x": round(x/norm, 3),
            "y": round(y/norm, 3),
            "z": round(z/norm, 3)}

def publish_data(client, topic, data):
    client.publish(topic, json.dumps(data))

def publish_imu(client):
    while True:
        timestamp = int(time.time() * 1000)
        accel = get_mock_accelerometer()
        gyro = get_mock_gyroscope()
        mag = get_mock_magnetometer()
        quat = get_mock_quaternion()
       
        imu_payload = {
            "device_id": AGENT_ID,
            "agent_name": AGENT_NAME,
            "timestamp": timestamp,
            "data": {
                "accelerometer_x": accel['x'],
                "accelerometer_y": accel['y'],
                "accelerometer_z": accel['z'],
                "gyroscope_x": gyro['x'],
                "gyroscope_y": gyro['y'],
                "gyroscope_z": gyro['z'],
                "magnetometer_x": mag['x'],
                "magnetometer_y": mag['y'],
                "magnetometer_z": mag['z'],
                "quaternion_w": quat['w'],
                "quaternion_x": quat['x'],
                "quaternion_y": quat['y'],
                "quaternion_z": quat['z']
            }
        }
        publish_data(client, f"Si/{AGENT_ID}/IMU", imu_payload)
        time.sleep(0.2)  # Publica IMU cada 0.2 segundos

def publish_gps(client):
    while True:
        timestamp = int(time.time() * 1000)
        gps_data = get_mock_gps()
    
        gps_payload = {
            "device_id": AGENT_ID,
            "agent_name": AGENT_NAME,
            "timestamp": timestamp,
            "data": {
                "latitud": gps_data['latitud'],
                "longitud": gps_data['longitud'],
                "altitud": gps_data['altitud'],
                "speed": gps_data['speed'],
                "satellites": gps_data['satellites'],
                "hdop": gps_data['hdop']
            }
        }
        publish_data(client, f"Si/{AGENT_ID}/GPS", gps_payload)
        time.sleep(0.3)  # Publica GPS cada 0.3 segundos

def publish_env(client):
    while True:
        timestamp = int(time.time() * 1000)
        env = get_mock_environment()
        env_payload = {
            "device_id": AGENT_ID,
            "agent_name": AGENT_NAME,
            "timestamp": timestamp,
            "data": {
                "temperature": env['temp'],
                "pressure": env['pressure'],
                "humidity": env['humidity']
            }
        }
        publish_data(client, f"Si/{AGENT_ID}/ENV", env_payload)
        time.sleep(0.5)  # Publica datos ambientales cada 0.5 segundos

def main():
    client = mqtt.Client()
    client.username_pw_set(USERNAME, PASSWORD)
    client.connect(BROKER, PORT, 60)
    client.loop_start()

    # Selección de sensores vía variables de entorno
    sensors = os.getenv("SENSORS", "imu,gps,env")
    sensor_list = [s.strip().lower() for s in sensors.split(",")]

    if "imu" in sensor_list:
        threading.Thread(target=publish_imu, args=(client,), daemon=True).start()
    if "gps" in sensor_list:
        threading.Thread(target=publish_gps, args=(client,), daemon=True).start()
    if "env" in sensor_list:
        threading.Thread(target=publish_env, args=(client,), daemon=True).start()

    while True:
        time.sleep(1)

if __name__ == "__main__":
    main()