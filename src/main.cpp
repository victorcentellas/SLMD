#include <WiFi.h>
#include <esp_now.h>
#include <esp_wifi.h>
#include <ArduinoJson.h>
#include <AsyncMqttClient.h>
#include <ESP32Ping.h> 
#include "sensor_payload.h" 
#define MQTT_RECONNECT_INTERVAL 3000  // 3 segundos
#define MQTT_BROKER  "192.168.192.154" // Dirección IP del broker MQTT
#define MQTT_PORT 1883               // Puerto del broker MQTT

const char* ssid     = "GL-MT300N-V2-0aa";
const char* password = "goodlife";
unsigned long lastReconnectAttempt = 0;


const char* user_mqtt = "root";
const char* password_mqtt = "tfg-2425";

AsyncMqttClient mqttClient;
bool shouldReconnect = false;

const char* mqtt_topic = "Si/";
int32_t peerChannel = 0;

int32_t getWiFiChannel(const char *ssid)
{
    if (int32_t n = WiFi.scanNetworks())
    {
        for (uint8_t i = 0; i < n; i++)
        {
            if (!strcmp(ssid, WiFi.SSID(i).c_str()))
            {
                return WiFi.channel(i);
            }
        }
    }

    return 0;
}
void sincronicePeers(const uint8_t *mac) {

    if(!esp_now_is_peer_exist(mac)){
      esp_now_peer_info_t peerInfo = {};
      memcpy(peerInfo.peer_addr, mac, 6);
      peerInfo.channel = peerChannel;
      peerInfo.encrypt = false;
  
      esp_now_add_peer(&peerInfo);
    }
    else{
      Serial.printf("\nPeer ya existe");
    }
  
  }


void connectToMqtt() {
  Serial.println("Intentando conectar a MQTT...");
  mqttClient.setServer(MQTT_BROKER, MQTT_PORT);
  mqttClient.setCredentials(user_mqtt, password_mqtt);
  mqttClient.setKeepAlive(120); 
  mqttClient.setClientId("ESP32-Gateway");
  
  // Registra callbacks que se mantendrán
  mqttClient.onMessage([](char* topic, char* payload, AsyncMqttClientMessageProperties properties,
                            size_t len, size_t index, size_t total) {
      Serial.printf("Mensaje recibido en el tema %s: %.*s\n", topic, len, payload);
  });
  mqttClient.onPublish([](uint16_t packetId) {
      Serial.printf("Mensaje publicado con ID %u\n", packetId);
  });
  
  // Intenta conectar y muestra un mensaje posterior
  Serial.println("Conectandose a MQTT...");
  mqttClient.connect();
}

void onMqttConnect(bool sessionPresent) {
  Serial.println("MQTT conectado exitosamente!");
  shouldReconnect = false;
}

void onMqttDisconnect(AsyncMqttClientDisconnectReason reason) {
  Serial.println("Desconectado de MQTT. Se intentará reconectar...");
  Serial.print("Razón de desconexión: ");
  shouldReconnect = true;

  switch(reason) {
      case AsyncMqttClientDisconnectReason::TCP_DISCONNECTED:
          Serial.println("TCP_DISCONNECTED");
          break;
      case AsyncMqttClientDisconnectReason::MQTT_UNACCEPTABLE_PROTOCOL_VERSION:
          Serial.println("MQTT_UNACCEPTABLE_PROTOCOL_VERSION");
          break;
      case AsyncMqttClientDisconnectReason::MQTT_IDENTIFIER_REJECTED:
          Serial.println("MQTT_IDENTIFIER_REJECTED");
          break;
      case AsyncMqttClientDisconnectReason::MQTT_SERVER_UNAVAILABLE:
          Serial.println("MQTT_SERVER_UNAVAILABLE");
          break;
      case AsyncMqttClientDisconnectReason::ESP8266_NOT_ENOUGH_SPACE:
          Serial.println("ESP8266_NOT_ENOUGH_SPACE");
          break;
      case AsyncMqttClientDisconnectReason::MQTT_NOT_AUTHORIZED:
          Serial.println("MQTT_NOT_AUTHORIZED");
          break;
      default:
          Serial.print((uint8_t)reason);
          break;
  }
}
void format_mac(const uint8_t *macAddr, char *mac_str) {
    snprintf(mac_str, 18, "%02X:%02X:%02X:%02X:%02X:%02X", 
             macAddr[0], macAddr[1], macAddr[2], macAddr[3], macAddr[4], macAddr[5]);
  }
uint8_t get_msg_type(const uint8_t *data) {
    return data[0];
  }
// Callback de recepción ESP-NOW
void onDataReceive(const uint8_t *mac, const uint8_t *data, int len) {
    sincronicePeers(mac); // Asegurarse de que el peer esté sincronizado
    Serial.println("Datos recibidos por ESP-NOW:");
    char mac_str[18];
    format_mac(mac, mac_str);
    uint8_t msg_type = get_msg_type(data);
    Serial.printf("\nMensaje recibido de %s\n", mac_str);
    Serial.printf("Tipo de mensaje: %d\n", msg_type);

    switch (msg_type) {
        case IMU_PAYLOAD: {
            Serial.println("Tipo de mensaje: IMU");
            SensorIMUPayload* imuPayload = (SensorIMUPayload*)data;
            char topicIMU[64];
            sprintf(topicIMU, "Si/%s/IMU", imuPayload->device_id);
            char imuCopy[128];
            memset(imuCopy, 0, sizeof(imuCopy)); // Inicializa el buffer con ceros

            strncpy(imuCopy, imuPayload->imu, sizeof(imuCopy));
            imuCopy[sizeof(imuCopy)-1] = '\0';

            
            float values[14];
            int idx = 0;
            char* token = strtok(imuCopy, ",");
            while(token != NULL && idx < 14) {
                values[idx++] = atof(token);
                token = strtok(NULL, ",");
            }
            
            if(idx != 14) {
                Serial.println("Error al parsear los datos IMU");
                break;
            }
        
            // Construir el JSON con la estructura deseada
            StaticJsonDocument<512> docImu;
            docImu["device_id"]   = imuPayload->device_id;
            docImu["agent_name"]  = "ESP32-Gateway";
            // Puedes usar imuPayload->timestamp o values[0] según convenga
            docImu["timestamp"]   = imuPayload->timestamp;
        
            JsonObject dataObj = docImu.createNestedObject("data");
            dataObj["accelerometer_x"] = values[1];
            dataObj["accelerometer_y"] = values[2];
            dataObj["accelerometer_z"] = values[3];
            dataObj["gyroscope_x"]     = values[4];
            dataObj["gyroscope_y"]     = values[5];
            dataObj["gyroscope_z"]     = values[6];
            dataObj["magnetometer_x"]  = values[7];
            dataObj["magnetometer_y"]  = values[8];
            dataObj["magnetometer_z"]  = values[9];
            dataObj["quaternion_w"]    = values[10];
            dataObj["quaternion_x"]    = values[11];
            dataObj["quaternion_y"]    = values[12];
            dataObj["quaternion_z"]    = values[13];
            char jsonBufferIMU[512];
            serializeJson(docImu, jsonBufferIMU);
            if(mqttClient.connected()) {
                Serial.println("MQTT conectado, publicando datos IMU...");
                mqttClient.publish(topicIMU, 0, false, jsonBufferIMU);
                Serial.print("IMU publicado en: ");
                Serial.println(topicIMU);
            } else {
                Serial.println("MQTT no conectado, intentando reconectar...");
                connectToMqtt();
            }
            
            break;
        }
        case GPS_PAYLOAD: {
            Serial.println("Tipo de mensaje: GPS");
            SensorGPSPayload* gpsPayload = (SensorGPSPayload*)data;
            char topicGPS[64];
            sprintf(topicGPS, "Si/%s/GPS", gpsPayload->device_id);
            char gpsCopy[64];
            strncpy(gpsCopy, gpsPayload->gps, sizeof(gpsCopy));
            gpsCopy[sizeof(gpsCopy)-1] = '\0';

            // Se esperan 7 valores: 
            // [0]: timestamp, [1]: latitud, [2]: longitud, [3]: altitud, [4]: velocidad, [5]: satélites, [6]: hdop
            float values[7];
            int idx = 0;
            char* token = strtok(gpsCopy, ",");
            while(token != NULL && idx < 7) {
                values[idx++] = atof(token);
                token = strtok(NULL, ",");
            }
            if(idx != 7) {
                Serial.println("Error al parsear los datos GPS");
                break;
            }

            // Construir el JSON con la estructura deseada.
            StaticJsonDocument<256> docGps;
            docGps["device_id"]   = gpsPayload->device_id;
            docGps["agent_name"]  = "ESP32-Gateway";
            docGps["timestamp"]   = gpsPayload->timestamp; // O bien values[0] si prefieres.
            
            JsonObject dataObj = docGps.createNestedObject("data");
            dataObj["lat"]         = values[1];
            dataObj["lng"]         = values[2];
            dataObj["altitude"]    = values[3];
            dataObj["speed"]       = values[4];
            dataObj["satellites"]  = values[5]; // Si es entero, podrías convertirlo.
            dataObj["hdop"]        = values[6];

            char jsonBufferGPS[256];
            serializeJson(docGps, jsonBufferGPS);
            mqttClient.publish(topicGPS, 0, false, jsonBufferGPS);
            if(mqttClient.connected()) {
                Serial.println("MQTT no conectado, intentando reconectar...");
                Serial.print("GPS publicado en: ");
                Serial.println(topicGPS);
            } else {
                Serial.println("MQTT no conectado, intentando reconectar...");
                connectToMqtt();
            }
           
            break;
        }
        case ENV_PAYLOAD: {
            Serial.println("Tipo de mensaje: ENV");
            SensorENVPayload* envPayload = (SensorENVPayload*)data;
            char topicENV[64];
            sprintf(topicENV, "Si/%s/ENV", envPayload->device_id);
            char envCopy[64];
            // Se asume que envPayload->env contiene datos formateados como: 
            // "timestamp,temp,pressure,humidity"
            strncpy(envCopy, envPayload->env, sizeof(envCopy));
            envCopy[sizeof(envCopy) - 1] = '\0';

            // Se esperan 4 valores:
            // [0]: timestamp (opcional, ya se tiene en envPayload->timestamp),
            // [1]: temperatura, [2]: presión y [3]: humedad
            float values[4];
            int idx = 0;
            char* token = strtok(envCopy, ",");
            while (token != NULL && idx < 4) {
                values[idx++] = atof(token);
                token = strtok(NULL, ",");
            }
            if (idx != 4) {
                Serial.println("Error al parsear los datos ENV");
                break;
            }

            // Construir el JSON con la estructura deseada:
            // "device_id": envPayload->device_id,
            // "agent_name": "ESP32-Gateway",
            // "timestamp": envPayload->timestamp,
            // "data": {
            //    "temperature": values[1],
            //    "pressure": values[2],
            //    "humidity": values[3]
            // }
            StaticJsonDocument<256> docEnv;
            docEnv["device_id"]  = envPayload->device_id;
            docEnv["agent_name"] = "ESP32-Gateway";
            // Puedes elegir usar el timestamp que ya viene en el payload o el que se parseó en values[0]
            docEnv["timestamp"]  = envPayload->timestamp; 

            JsonObject dataObj = docEnv.createNestedObject("data");
            dataObj["temperature"] = values[1];
            dataObj["pressure"]    = values[2];
            dataObj["humidity"]    = values[3];

            char jsonBufferENV[256];
            serializeJson(docEnv, jsonBufferENV);
            if(mqttClient.connected()) {
                Serial.println("MQTT conectado, publicando datos ENV...");
                mqttClient.publish(topicENV, 0, false, jsonBufferENV);
                Serial.print("ENV publicado en: ");
                Serial.println(topicENV);
            } else {
                Serial.println("MQTT no conectado, intentando reconectar...");
                connectToMqtt();
            }
            
            break;
        }
        default: {
            Serial.println("Tipo de mensaje desconocido");
            return; // Salir si el tipo de mensaje no es válido
        }
    }
    
  }
void setup() {
  Serial.begin(115200);
  Serial.println("Gateway iniciado");

  // Inicializar Wi-Fi
  WiFi.mode(WIFI_STA);
  peerChannel = getWiFiChannel(ssid);
  WiFi.begin(ssid, password);
  Serial.print("Conectando a Wi-Fi");
  esp_wifi_set_ps(WIFI_PS_NONE); // Desactivar el modo de ahorro de energía
  esp_wifi_set_channel(peerChannel, WIFI_SECOND_CHAN_NONE); 
  Serial.printf("\nCanal: %d", peerChannel);


  while (WiFi.status() != WL_CONNECTED) {
      delay(500);
      Serial.print(".");
  }
  Serial.println(" Conectado a Wi-Fi");
  Serial.print("IP del ESP: ");
  Serial.println(WiFi.localIP());
  Serial.print("MAC del ESP: ");
    Serial.println(WiFi.macAddress());

  // (Opcional) Verificar que se puede alcanzar el broker
  if(Ping.ping(MQTT_BROKER)) {
      Serial.println("Se puede hacer ping al broker");
  } else {
      Serial.println("No se puede hacer ping al broker");
  }

  // Registrar callbacks MQTT
  mqttClient.onDisconnect(onMqttDisconnect);
  mqttClient.onConnect(onMqttConnect);
  connectToMqtt();

  // Inicializar ESP-NOW
  if (esp_now_init() != ESP_OK) {
      Serial.println("Error al inicializar ESP-NOW");
      while (true) {
          delay(100);
      }
  }
  esp_now_register_recv_cb(onDataReceive);
  Serial.println("ESP-NOW iniciado y callback registrado");
}

void loop() {
    unsigned long now = millis();
    if (!mqttClient.connected() && shouldReconnect && (now - lastReconnectAttempt > MQTT_RECONNECT_INTERVAL)) {
        lastReconnectAttempt = now;
        Serial.println("Intentando reconectar MQTT desde loop...");
        connectToMqtt();
    }
}