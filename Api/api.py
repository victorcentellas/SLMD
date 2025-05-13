from fastapi import FastAPI, HTTPException
from influxdb_client import InfluxDBClient, client
import subprocess
import redis

# Configuración de conexión a Redis
REDIS_HOST = "192.168.192.156"
REDIS_PORT = 6379
redis_client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)

# Configuración de conexión a InfluxDB
INFLUXDB_URL = "http://192.168.192.156:8086"
INFLUXDB_TOKEN = "hQuGGvtteZvXhCdiTE_CcG1MCIOFe_D4o8HJUWonWKhOx2jyUqUsckGTJKeboN0hK83M1MWpjS-fvgyAWDw1hA=="
INFLUXDB_ORG = "UCLM"
INFLUXDB_BUCKET = "datos"
influx_client = InfluxDBClient(url=INFLUXDB_URL, token=INFLUXDB_TOKEN)
write_api = influx_client.write_api(write_options=client.write_api.SYNCHRONOUS)
query_api = influx_client.query_api()

# FastAPI app
app = FastAPI()

# Obtener la lista de sensores
@app.get("/sensores/")
def listar_sensores():
    # Recuperar todas las claves de Redis que sigan el patrón "id:sensor*"
    sensor_keys = redis_client.keys("id:sensor*")
    
    if not sensor_keys:
        raise HTTPException(status_code=404, detail="No se encontraron sensores")
    
    sensores = []
    
    # Iterar sobre las claves encontradas y obtener información
    for key in sensor_keys:
        # Cada clave será como 'id:sensor1' o 'id:sensor2', por lo que podemos obtener el tipo y la ubicación
        key_parts = key.split(":")
        tipo = key_parts[1]
        
        sensores.append({
            "tipo": tipo,
            "sensor_id": redis_client.get(key)
        })
    
    return {"sensores": sensores}

@app.post("/crear_sensor/{sensor_name}")
def crear_sensor(sensor_name: str):
    # Verificar si el sensor ya existe en Redis
    if redis_client.get(f"id:{sensor_name}"):
        raise HTTPException(status_code=400, detail="El sensor ya existe")

    # Ejecutar el comando docker para crear el contenedor con el sensor
    try:
        result = subprocess.run(
            [
                "docker", "run", "-d", "--rm", "--name", sensor_name, 
                "--network", "emqx-network", "-e", f"AGENT_NAME={sensor_name}", 
                "agente-sensor"
            ],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )

        return {"message": f"Sensor {sensor_name} creado con éxito", "sensor_id": result.stdout.decode("utf-8")}
    
    except subprocess.CalledProcessError as e:
        raise HTTPException(status_code=500, detail=f"Error al crear el sensor: {e.stderr.decode('utf-8')}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/sensor/{sensor_name}/info")
def listar_informacion(sensor_name: str):
    sensor_id = redis_client.get(f"id:{sensor_name}")

    if not sensor_id:
        raise HTTPException(status_code=404, detail="No se encontró ese sensor")
    # Si el UUID existe, consultar los datos en InfluxDB
    query = f'''
         from(bucket: "{INFLUXDB_BUCKET}")
            |> range(start: -1d)  
            |> filter(fn: (r) => r["topic"] == "Si/{sensor_id}/10DOF" or r["topic"] == "Si/{sensor_id}/GPS")
            |> filter(fn: (r) => r["_field"] == "id" or
                                  r["_field"] == "sensor" or
                                  r["_field"] == "tipo")
            |> last()  

        '''
    result = query_api.query(query, org=INFLUXDB_ORG)

    if not result:
        raise HTTPException(status_code=404, detail="Datos del sensor no encontrados en InfluxDB")
    # Obtener los campos (_field) de la respuesta
    fields = [{"field": record.get_field(), "value": record.get_value()} for table in result for record in table.records]

    # Verificación si no se encuentran datos
    if not fields:
        raise HTTPException(status_code=404, detail="Datos del sensor no encontrados en InfluxDB")

    # Retornar los resultados
    return {"Informacion": fields}

@app.get("/sensor/{sensor_name}/campos")
def listar_campos(sensor_name: str):
    sensor_id = redis_client.get(f"id:{sensor_name}")

    if not sensor_id:
        raise HTTPException(status_code=404, detail="No se encontró ese sensor")
    print(f"{sensor_id}")
    # Si el UUID existe, consultar los datos en InfluxDB
    query = f'''
        import "influxdata/influxdb/schema"
        schema.fieldKeys(
        bucket: "{INFLUXDB_BUCKET}",
        predicate: (r) => r.topic == "Si/{sensor_id}/GPS" or r.topic == "Si/{sensor_id}/10DOF" ,
        start: -1d
        )
        '''
    result = query_api.query(query, org=INFLUXDB_ORG)
    fields = [record.get_value() for table in result for record in table.records]
    print("Campos (_field) encontrados:", fields)
    if not result:
        raise HTTPException(status_code=404, detail="Datos del sensor no encontrados en InfluxDB")
    return {"fields" : fields}
