#ifndef SENSOR_PAYLOADS_H
#define SENSOR_PAYLOADS_H

#pragma pack(push, 1)
#include <stdint.h>

typedef enum
{
  IMU_PAYLOAD = (uint8_t)0x00,
  GPS_PAYLOAD,
  ENV_PAYLOAD

 

} MessageType;
struct SensorIMUPayload {
    MessageType type;
    char device_id[9];    // 8 caracteres + terminador
    uint64_t timestamp;
    char imu[128];        // Datos IMU
};

struct SensorGPSPayload {
    MessageType type;
    char device_id[9];
    uint64_t timestamp;
    char gps[64];         // Datos GPS
};

struct SensorENVPayload {
    MessageType type;
    char device_id[9];
    uint64_t timestamp;
    char env[64];         // Datos ambientales
};
#pragma pack(pop)

#endif