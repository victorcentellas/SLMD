from fastapi import FastAPI, HTTPException
from influxdb_client import InfluxDBClient, client
import subprocess
import redis
import docker
import uuid



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


# Cliente Docker
docker_client = docker.from_env()

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

@app.get("/sensores/activos")
def listar_sensores_activos():
    sensor_keys = redis_client.keys("id:*")
    activos = []
    for key in sensor_keys:
        sensor_name = key.split("id:")[-1]
        try:
            container = docker_client.containers.get(sensor_name)
            container.reload()
            if container.status == "running":
                activos.append({
                    "sensor": sensor_name,
                    "sensor_id": redis_client.get(key)
                })
        except docker.errors.NotFound:
            continue
        except Exception:
            continue
    if not activos:
        raise HTTPException(status_code=404, detail="No se encontraron sensores activos")
    return {"sensores_activos": activos}

@app.get("/sensores/inactivos")
def listar_sensores_inactivos():
    sensor_keys = redis_client.keys("id:*")
    inactivos = []
    for key in sensor_keys:
        sensor_name = key.split("id:")[-1]
        try:
            container = docker_client.containers.get(sensor_name)
            container.reload()
            if container.status != "running":
                inactivos.append({
                    "sensor": sensor_name,
                    "sensor_id": redis_client.get(key)
                })
        except docker.errors.NotFound:
            inactivos.append({
                "sensor": sensor_name,
                "sensor_id": redis_client.get(key)
            })
        except Exception:
            continue
    if not inactivos:
        raise HTTPException(status_code=404, detail="No se encontraron sensores inactivos")
    return {"sensores_inactivos": inactivos}



@app.post("/crear_sensor/{sensor_name}")
def crear_sensor(sensor_name: str):
     # Verificar si el sensor ya existe en Redis

    if redis_client.get(f"id:{sensor_name}"):
        raise HTTPException(status_code=400, detail="El sensor ya existe")
    # Generar un UUID único para el sensor
    sensor_id = str(uuid.uuid4())[:8]

    try:
        container = docker_client.containers.run(
            "agente-sensor", 
            detach=True, 
            #remove=True, 
            name=sensor_name, 
            network="emqx-network", 
            environment={"AGENT_NAME": sensor_name, "AGENT_ID":sensor_id },
        )

        return {"message": f"Sensor {sensor_name} creado con éxito", "sensor_id": sensor_id}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/sensor/{sensor_name}/variable/{var_name}/{start}/{stop}")
def obtener_variable(sensor_name: str, var_name: str, start: str , stop: str ):
    sensor_id = redis_client.get(f"id:{sensor_name}")
    if not sensor_id:
        raise HTTPException(status_code=404, detail="Sensor no encontrado")
    
    query = f'''
        from(bucket: "{INFLUXDB_BUCKET}")
            |> range(start: {start}, stop: {stop})
            |> filter(fn: (r) => r.topic == "Si/{sensor_id}/IMU" or r.topic == "Si/{sensor_id}/GPS" or r.topic == "Si/{sensor_id}/ENV")
            |> filter(fn: (r) => r._field == "{var_name}")
            |> aggregateWindow(every: 1s, fn: last, createEmpty: false)
            |> yield(name: "last")    
            '''
    result = query_api.query(query, org=INFLUXDB_ORG)
    datos = [
        {"value": record.get_value(), "timestamp": record.get_time().isoformat()}
        for table in result for record in table.records
    ]
    
    if not datos:
        raise HTTPException(status_code=404, detail=f"No se encontraron datos para la variable {var_name}")
    
    return {"variable": var_name, "datos": datos}
@app.get("/sensor/{sensor_name}/metricas_interval/{start}/{stop}")
def listar_metricas_interval(sensor_name: str, start: str, stop: str):
    sensor_id = redis_client.get(f"id:{sensor_name}")
    if not sensor_id:
        raise HTTPException(status_code=404, detail="Sensor no encontrado")

    metricas = {}
    for metrica in ["IMU", "GPS", "ENV"]:
        query = f'''
            from(bucket: "{INFLUXDB_BUCKET}")
                |> range(start: {start}, stop: {stop})
                |> filter(fn: (r) => r.topic == "Si/{sensor_id}/{metrica}")
                |> aggregateWindow(every: 1s, fn: last, createEmpty: false)
                |> yield(name: "last")
        '''
        result = query_api.query(query, org=INFLUXDB_ORG)
        campos = [
            {"field": record.get_field(), "value": record.get_value(),"timestamp": record.get_time().isoformat()}
            for table in result for record in table.records
            if record.get_field() not in ["agent_name", "device_id"]

        ]   
        metricas[metrica] = campos if campos else []
    
    return {"metricas": metricas}

@app.get("/sensor/{sensor_name}/metricas/{tipo_sensor}")
def listar_metrica_sensor(sensor_name: str, metrica: str):
    sensor_id = redis_client.get(f"id:{sensor_name}")
    if not sensor_id:
        raise HTTPException(status_code=404, detail="Sensor no encontrado")
    if metrica not in ["IMU", "GPS", "ENV"]:
        raise HTTPException(status_code=400, detail="Métrica inválida. Use 'IMU', 'GPS' o 'ENV'")
    
    query = f'''
        from(bucket: "{INFLUXDB_BUCKET}")
            |> range(start: -1d)
            |> filter(fn: (r) => r.topic == "Si/{sensor_id}/{metrica}")
            |> last()
    '''
    result = query_api.query(query, org=INFLUXDB_ORG)
    campos = [{"field": record.get_field(), "value": record.get_value()} 
              for table in result for record in table.records]
    if not campos:
        raise HTTPException(status_code=404, detail="No se encontraron datos para la métrica")
    return {"metrica": metrica, "datos": campos}



@app.get("/sensor/{sensor_name}/campos")
def listar_variables_interes(sensor_name: str):
    sensor_id = redis_client.get(f"id:{sensor_name}")
    if not sensor_id:
        raise HTTPException(status_code=404, detail="Sensor no encontrado")
    
    query = f'''
        import "influxdata/influxdb/schema"
        schema.fieldKeys(
            bucket: "{INFLUXDB_BUCKET}",
            predicate: (r) => r.topic == "Si/{sensor_id}/IMU" or r.topic == "Si/{sensor_id}/GPS" or r.topic == "Si/{sensor_id}/ENV",
            start: -1d
        )
    '''
    result = query_api.query(query, org=INFLUXDB_ORG)
    variables = [record.get_value() for table in result for record in table.records]
    if not variables:
        raise HTTPException(status_code=404, detail="No se encontraron variables de interés")
    return {"variables": variables}


@app.get("/sensor/{sensor_name}/grupo/{grupo}/{start}/{stop}")
def obtener_medidas_grupo(sensor_name: str, grupo: str, start: str, stop: str):
    sensor_id = redis_client.get(f"id:{sensor_name}")
    if not sensor_id:
        raise HTTPException(status_code=404, detail="Sensor no encontrado")
        
    query = f'''
        import "strings"
        from(bucket: "{INFLUXDB_BUCKET}")
            |> range(start: {start}, stop: {stop})
            |> filter(fn: (r) => r.topic == "Si/{sensor_id}/IMU")
            |> filter(fn: (r) => strings.containsStr(v: r._field, substr: "{grupo}"))
            |> aggregateWindow(every: 1s, fn: last, createEmpty: false)
            |> pivot(rowKey: ["_time"], columnKey: ["_field"], valueColumn: "_value")
            |> yield(name: "last")
    '''
    result = query_api.query(query, org=INFLUXDB_ORG)
    datos = []
    for table in result:
        for record in table.records:
            # Se filtran claves internas que no interesan
            values = { key: record.values[key]
                       for key in record.values 
                       if key not in ["_time", "result", "table", "_start", "_stop", "_measurement", "host", "topic"] }
            datos.append({
                "timestamp": record.get_time().isoformat(),
                "values": values
            })
    
    if not datos:
        raise HTTPException(status_code=404, detail=f"No se encontraron registros para el grupo {grupo}")
    
    return {"grupo": grupo, "datos": datos}


@app.post("/sensor/{sensor_name}/start")
def start_sensor(sensor_name: str):
    try:
        container = docker_client.containers.get(sensor_name)
        container.start()
        return {"message": f"Sensor {sensor_name} iniciado."}
    except docker.errors.NotFound:
        raise HTTPException(status_code=404, detail="Sensor no encontrado")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/sensor/{sensor_name}/stop")
def stop_sensor(sensor_name: str):
    try:
        container = docker_client.containers.get(sensor_name)
        container.stop()
        return {"message": f"Sensor {sensor_name} detenido."}
    except docker.errors.NotFound:
        raise HTTPException(status_code=404, detail="Sensor no encontrado")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/sensor/{sensor_name}")
def delete_sensor(sensor_name: str):
    try:
        container = docker_client.containers.get(sensor_name)
        container.remove(force=True)
        redis_client.delete(f"id:{sensor_name}")
        return {"message": f"Sensor {sensor_name} eliminado."}
    except docker.errors.NotFound:
        raise HTTPException(status_code=404, detail="Sensor no encontrado")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


