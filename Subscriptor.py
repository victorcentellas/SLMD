#!/usr/bin/env python3

import paho.mqtt.client as mqtt
import json

# Configuración del broker MQTT
BROKER = "localhost"
PORT = 1883
USERNAME = "user1"
PASSWORD = "clave123"
TOPIC = "sensor/#"  # Suscribirse a todos los sensores

def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("Conectado al broker MQTT")
        client.subscribe(TOPIC)  # Suscribirse a todos los datos del sensor
    else:
        print(f"Error de conexión: {rc}")

def on_message(client, userdata, msg):
    try:
        payload = json.loads(msg.payload.decode("utf-8"))
        print(f"Mensaje recibido en {msg.topic}: {json.dumps(payload, indent=2)}")
    except json.JSONDecodeError:
        print(f"Error decodificando JSON en {msg.topic}: {msg.payload}")

def main():
    client = mqtt.Client()
    client.username_pw_set(USERNAME, PASSWORD)
    client.on_connect = on_connect
    client.on_message = on_message
    
    client.connect(BROKER, PORT, 60)
    client.loop_forever()  # Mantener el suscriptor activo

if __name__ == "__main__":
    main()
