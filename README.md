# Publicación de datos en MQTT

## Formato del tópico de publicación
Para publicar datos en **MQTT**, se debe seguir la siguiente estructura de tópico:

```plaintext
sensor/ID/METRICA
```

Donde:
- **ID** es un identificador único generado de la siguiente manera:
  
  ```python
  import uuid
  ID = str(uuid.uuid4())
  ```
  
  Ejemplo de un ID generado:
  
  ```plaintext
  28c40769-1919-420a-8eb1-7449d56a0a7f
  ```
- **METRICA** representa el tipo de sensor del cual se están enviando datos. Las métricas disponibles son:
  
  - `acelerometro`
  - `giroscopio`
  - `magnetometro`
  - `barometro`
  - `gps`

## Formato de los datos
Los datos se deben enviar en formato **JSON**, de la siguiente manera:

### Ejemplo de publicación:

```json
{
  "acelerometro": {
    "x": -8.257,
    "y": -8.256,
    "z": -8.256
  },
  "giroscopio": {
    "x": -1032.024,
    "y": -1032.015,
    "z": -1032.009
  },
  "magnetometro": {
    "x": -2528.401,
    "y": -2528.39,
    "z": -2528.373
  },
  "barometro": {
    "presion": 502.005
  },
  "gps": {
    "hora": "210401",
    "latitud": 40.012421,
    "longitud": -2.987579
  }
}
```

