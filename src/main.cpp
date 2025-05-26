#include <WiFi.h>
#include <esp_now.h>
#include <PubSubClient.h>
#include <ArduinoJson.h> // Asegúrate de instalar la librería ArduinoJson

// Configuración de Wi-Fi y MQTT
const char* ssid     = "DIGIFIBRA-AE85";
const char* password = "TLJG7K3LX8";
const char* mqtt_server = "192.168.192.154";
const char* user_mqtt = "root";
const char* password_mqtt = "tfg-2425";

WiFiClient espClient;
PubSubClient mqttClient(espClient);

// Tema donde se publicarán los datos
const char* mqtt_topic = "sensor/data";

// Función que intenta reconectar al broker MQTT
void reconnectMQTT() {
    while (!mqttClient.connected()) {
        Serial.print("Conectando al broker MQTT...");
        if (mqttClient.connect("GatewayClient", user_mqtt, password_mqtt)) {
            Serial.println("Conectado al broker MQTT");
        } else {
            Serial.print("Error de conexión MQTT, rc=");
            Serial.print(mqttClient.state());
            Serial.println(" reintentando en 2 segundos...");
            delay(2000);
        }
    }
}

// Callback de ESP-NOW: se llama al recibir datos de un nodo sensor
void onDataReceive(const uint8_t *mac, const uint8_t *incomingData, int len) {
  // Mostrar la dirección MAC del nodo sensor
  char macStr[18];
  sprintf(macStr, "%02X:%02X:%02X:%02X:%02X:%02X",
          mac[0], mac[1], mac[2], mac[3], mac[4], mac[5]);
  Serial.print("Datos recibidos desde: ");
  Serial.println(macStr);

  // Convertir los datos recibidos a String (payload JSON)
  String data = "";
  for (int i = 0; i < len; i++) {
      data += (char)incomingData[i];
  }
  Serial.println("Payload recibido:");
  Serial.println(data);

  // Parsear el JSON recibido
  const size_t capacity = 1024;
  DynamicJsonDocument doc(capacity);
  DeserializationError error = deserializeJson(doc, data);
  if (error) {
      Serial.print("Error al parsear JSON: ");
      Serial.println(error.f_str());
  } else {
      // Extraer campos principales según la estructura enviada por el nodo
      const char* deviceID = doc["device_id"];
      unsigned long timestamp = doc["timestamp"];
      const char* imuData = doc["imu"]["data"];
      const char* gpsData = doc["gps"]["data"];
      const char* envData = doc["env"]["data"];

      // Imprimir algunos campos extraídos
      Serial.print("Device ID: ");
      Serial.println(deviceID);
      Serial.print("Timestamp: ");
      Serial.println(timestamp);
      Serial.print("IMU Data: ");
      Serial.println(imuData);
      Serial.print("GPS Data: ");
      Serial.println(gpsData);
      Serial.print("ENV Data: ");
      Serial.println(envData);
  }

  // Publicar el mensaje completo en el broker MQTT
  // if (!mqttClient.connected()) {
  //     reconnectMQTT();
  // }
  // if (mqttClient.publish(mqtt_topic, data.c_str())) {
  //     Serial.println("Datos publicados en MQTT exitosamente");
  // } else {
  //     Serial.println("Error al publicar datos en MQTT");
  // }
}

void setup() {
    Serial.begin(115200);
    Serial.println("Gateway iniciado");

    // Inicializar Wi-Fi en modo estación y conectarse
    WiFi.mode(WIFI_STA);
    WiFi.begin(ssid, password);
    Serial.print("Conectando a Wi-Fi");
    while (WiFi.status() != WL_CONNECTED) {
        delay(500);
        Serial.print(".");
    }
    Serial.println(" Conectado a Wi-Fi");

    // Inicializar MQTT
    mqttClient.setServer(mqtt_server, 1883);
    reconnectMQTT();

    // Inicializar ESP-NOW
    if (esp_now_init() != ESP_OK) {
        Serial.println("Error al inicializar ESP-NOW");
        while (true) {
            delay(100);
        }
    }
    // Registrar callback para recepción de datos vía ESP-NOW
    esp_now_register_recv_cb(onDataReceive);
    Serial.println("ESP-NOW iniciado y callback registrado");
}

void loop() {
    mqttClient.loop();
}