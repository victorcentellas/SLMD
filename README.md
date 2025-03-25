## 🔄 **Flujo de Datos || Hecho por el momento**
1.**Agente.py**:
      - Estos agentes publicarán los datos en los tópicos de manera simultanea.
      - Esta realizado con docker para que se escale horizontalmente.
      - Estos datos serán por el momento fabricados.
      - Se conecta al broker MQTT (`emqx`) y pública dichos datos.

2.**EMQX**:
      - Está dockerizado.
      - Está configurado de manera que solo se permitan realizar acciones a través de usuarios.

3. **Telegraf** se conecta al broker MQTT (`emqx`) para obtener métricas y datos:  
   - Se conecta al broker MQTT (`tcp://emqx:1883`) y escucha las siguientes rutas:  
     - `Si/+/10DOF` – Sensores de 10 grados de libertad.  
     - `Si/+/GPS` – Datos de posición GPS.  
  
4. **Telegraf** procesa los datos en formato JSON y los envía a **InfluxDB** usando el plugin `outputs.influxdb_v2`:
   - URL: `http://influxdb:8086`  
   - Bucket: `datos`  
   - Organización: `UCLM`  
   - Token para autenticación.  

5. **InfluxDB** almacena los datos como series temporales.  
   - La estructura de los datos incluye etiquetas (`tags`) y valores (`fields`).  
   - Las consultas pueden realizarse mediante HTTP o desde Grafana.

6. **Automatizacion/Grafana**:
   - A través de un script se conectará con influxDB y se comprobará si hay nuevos sensores disponibles.
   - Se procederá a realizar consultas con Flux para recoger los sensores junto a sus métricas.
   - Se crearán automaticamente tantos dashboards como métricas haya en un sensor.

## **Infraestractura del sistema**
![Diagrama de la Infraestructura](https://github.com/victorcentellas/SLMD/blob/4cca46f637a19948248fe52d5824018433f119f5/Infraestructura-SLMD.drawio.png)

##  **Publicación de datos en MQTT**
## Formato del tópico de publicación
Para publicar datos en **MQTT**, se debe seguir la siguiente estructura de tópico:

```plaintext
Si/ID/METRICA
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
  
  - `10DOF`
  - `GPS`

## Formato de los datos
Los datos se deben enviar en formato **JSON**, de la siguiente manera:

### Ejemplo de publicación:

```json

  "Si/id/10DOF": {
    "id" = "28c40769-1919-420a-8eb1-7449d56a0a7f",
    "sensor" = "10DOF",
    "data":{
  "acelerometro_x": 3.5,  
  "acelerometro_y": 0.2, 
  "acelerometro_z": -9.8, 
  "giroscopio_x": 0.05,  
  "giroscopio_y": -0.03,  
  "giroscopio_z": 1.2,    
  "magnetometro_x": 12.5, 
  "magnetometro_y": -5.6,
  "magnetometro_z": 42.1, 
  "presion": 1013.25 
    },
    "timestamp":"2025-03-18T12:30:45Z"

}
  "Si/id/GPS": {
    "id" = "28c40769-1919-420a-8eb1-7449d56a0a7f",
    "sensor" = "GPS",
    "data":{
    "hora": "210401",
    "latitud": 40.012421,
    "longitud": -2.987579
    },
    "timestamp":"2025-03-18T12:30:45Z"
  }

```
##  **Factores a tener en cuenta**
## Ejecución de Agentes
Después de hacer un build :
```
docker build -t "nombre" .
```
Para ejecutar dicho contenedor con la opcion de network: emqx-network para que se pueda conectar a emqx y asi publicar dichos datos 
```
docker run --name "sensor1" --network "nombre-network" "nombre"
```

