from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel
from typing import List, Dict, Any
from influxdb_client import InfluxDBClient, client
import redis
import docker
import uuid

# --------------------------------------------------
# Configuración (mantén estos valores según tu entorno)
# --------------------------------------------------
REDIS_HOST = "192.168.192.156"
REDIS_PORT = 6379

INFLUXDB_URL = "http://192.168.192.156:8086"
INFLUXDB_TOKEN = "hQuGGvtteZvXhCdiTE_CcG1MCIOFe_D4o8HJUWonWKhOx2jyUqUsckGTJKeboN0hK83M1MWpjS-fvgyAWDw1hA=="
INFLUXDB_ORG = "UCLM"
INFLUXDB_BUCKET = "datos"

# --------------------------------------------------
# Funciones de dependencia
# --------------------------------------------------
def get_redis_client() -> redis.Redis:
    return redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)

def get_influx_query_api():
    influx_client = InfluxDBClient(url=INFLUXDB_URL, token=INFLUXDB_TOKEN)
    return influx_client.query_api()

def get_docker_client() -> docker.DockerClient:
    return docker.from_env()

# --------------------------------------------------
# Configuración de FastAPI y modelos
# --------------------------------------------------
app = FastAPI(
    title="API de Sensores",
    version="1.0.0",
    description="API para la gestión y consulta de sensores y sus métricas"
)

# Modelos Pydantic para respuestas
class Sensor(BaseModel):
    tipo: str
    sensor_id: str

class SensorList(BaseModel):
    sensores: List[Sensor]

class VariableResponse(BaseModel):
    variable: str
    datos: List[Dict[str, Any]]

class GrupoResponse(BaseModel):
    grupo: str
    datos: List[Dict[str, Any]]

# ---------------------
# Endpoints de Sensores
# ---------------------
@app.get("/sensores/", tags=["Sensores"], response_model=SensorList, summary="Listar todos los sensores")
def listar_sensores(redis_client: redis.Redis = Depends(get_redis_client)):
    sensor_keys = redis_client.keys("id:sensor*")
    if not sensor_keys:
        raise HTTPException(status_code=404, detail="No se encontraron sensores")
    sensores = []
    for key in sensor_keys:
        key_parts = key.split(":")
        tipo = key_parts[1]
        sensores.append(Sensor(tipo=tipo, sensor_id=redis_client.get(key)))
    return {"sensores": sensores}

@app.get("/sensores/activos", tags=["Sensores"], summary="Listar sensores activos")
def listar_sensores_activos(
    redis_client: redis.Redis = Depends(get_redis_client),
    docker_client: docker.DockerClient = Depends(get_docker_client)
):
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

@app.get("/sensores/inactivos", tags=["Sensores"], summary="Listar sensores inactivos")
def listar_sensores_inactivos(redis_client: redis.Redis = Depends(get_redis_client),
                              docker_client: docker.DockerClient = Depends(get_docker_client)):
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

@app.post("/crear_sensor/{sensor_name}", tags=["Gestión de Sensores"], summary="Crear sensor")
def crear_sensor(sensor_name: str,
                 redis_client: redis.Redis = Depends(get_redis_client),
                 docker_client: docker.DockerClient = Depends(get_docker_client)):
    if redis_client.get(f"id:{sensor_name}"):
        raise HTTPException(status_code=400, detail="El sensor ya existe")
    sensor_id = str(uuid.uuid4())[:8]
    try:
        container = docker_client.containers.run(
            "agente-sensor", 
            detach=True, 
            name=sensor_name, 
            network="emqx-network", 
            environment={"AGENT_NAME": sensor_name, "AGENT_ID": sensor_id},
        )
        return {"message": f"Sensor {sensor_name} creado con éxito", "sensor_id": sensor_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/sensor/{sensor_name}/start", tags=["Gestión de Sensores"], summary="Iniciar sensor")
def start_sensor(sensor_name: str,
                 docker_client: docker.DockerClient = Depends(get_docker_client)):
    try:
        container = docker_client.containers.get(sensor_name)
        container.start()
        return {"message": f"Sensor {sensor_name} iniciado."}
    except docker.errors.NotFound:
        raise HTTPException(status_code=404, detail="Sensor no encontrado")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/sensor/{sensor_name}/stop", tags=["Gestión de Sensores"], summary="Detener sensor")
def stop_sensor(sensor_name: str,
                docker_client: docker.DockerClient = Depends(get_docker_client)):
    try:
        container = docker_client.containers.get(sensor_name)
        container.stop()
        return {"message": f"Sensor {sensor_name} detenido."}
    except docker.errors.NotFound:
        raise HTTPException(status_code=404, detail="Sensor no encontrado")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/sensor/{sensor_name}", tags=["Gestión de Sensores"], summary="Eliminar sensor")
def delete_sensor(sensor_name: str,
                  redis_client: redis.Redis = Depends(get_redis_client),
                  docker_client: docker.DockerClient = Depends(get_docker_client)):
    try:
        container = docker_client.containers.get(sensor_name)
        container.remove(force=True)
        redis_client.delete(f"id:{sensor_name}")
        return {"message": f"Sensor {sensor_name} eliminado."}
    except docker.errors.NotFound:
        raise HTTPException(status_code=404, detail="Sensor no encontrado")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# --------------------------
# Endpoints de Consultas
# --------------------------
@app.get(
    "/sensor/{sensor_name}/variable/{var_name}/{start}/{stop}",
    tags=["Variables"],
    response_model=VariableResponse,
    summary="Obtener variable por intervalo",
    description="Consulta una variable publicada en cualquiera de los tópicos: IMU, GPS o ENV"
)
def obtener_variable(
    sensor_name: str,
    var_name: str,
    start: str,
    stop: str,
    redis_client: redis.Redis = Depends(get_redis_client),
    query_api = Depends(get_influx_query_api)
):
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

@app.get(
    "/sensor/{sensor_name}/grupo/{tipo_sensor}/{start}/{stop}",
    tags=["Grupos de Medidas"],
    response_model=GrupoResponse,
    summary="Obtener medidas por intervalo por tipo de sensor",
    description="Agrupa registros de la métrica del tipo de sensor indicado (IMU, GPS o ENV) y devuelve una fila por ventana."
)
def obtener_medidas_grupo_por_tipo(
    sensor_name: str,
    tipo_sensor: str,
    start: str,
    stop: str,
    redis_client: redis.Redis = Depends(get_redis_client),
    query_api = Depends(get_influx_query_api)
):
    sensor_id = redis_client.get(f"id:{sensor_name}")
    if not sensor_id:
        raise HTTPException(status_code=404, detail="Sensor no encontrado")
    if tipo_sensor not in ["IMU", "GPS", "ENV"]:
        raise HTTPException(status_code=400, detail="Tipo de sensor inválido. Use 'IMU', 'GPS' o 'ENV'")
    
    query = f'''
        from(bucket: "{INFLUXDB_BUCKET}")
            |> range(start: {start}, stop: {stop})
            |> filter(fn: (r) => r.topic == "Si/{sensor_id}/{tipo_sensor}")
            |> aggregateWindow(every: 1s, fn: last, createEmpty: false)
            |> pivot(rowKey: ["_time"], columnKey: ["_field"], valueColumn: "_value")
            |> yield(name: "last")
    '''
    result = query_api.query(query, org=INFLUXDB_ORG)
    datos = []
    for table in result:
        for record in table.records:
            values = {
                key: record.values[key]
                for key in record.values
                if key not in [
                    "_time", "result", "table", "_start", "_stop",
                    "_measurement", "host", "topic"
                ]
            }
            datos.append({
                "timestamp": record.get_time().isoformat(),
                "values": values
            })
    if not datos:
        raise HTTPException(status_code=404, detail=f"No se encontraron registros para el grupo {tipo_sensor}")
    return {"grupo": tipo_sensor, "datos": datos}

@app.get(
    "/sensor/{sensor_name}/grupo_medidas/{grupo}/{start}/{stop}",
    tags=["Grupos de Medidas"],
    response_model=GrupoResponse,
    summary="Obtener grupo de medidas por intervalo",
    description="Agrupa registros de la métrica IMU que contienen el patrón indicado (por ejemplo, 'data_accelerometer_') y devuelve una fila por ventana."
)
def obtener_medidas_grupo(
    sensor_name: str,
    grupo: str,
    start: str,
    stop: str,
    redis_client: redis.Redis = Depends(get_redis_client),
    query_api = Depends(get_influx_query_api)
):
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
            values = {
                key: record.values[key]
                for key in record.values
                if key not in [
                    "_time", "result", "table", "_start", "_stop",
                    "_measurement", "host", "topic"
                ]
            }
            datos.append({
                "timestamp": record.get_time().isoformat(),
                "values": values
            })
    if not datos:
        raise HTTPException(status_code=404, detail=f"No se encontraron registros para el grupo {grupo}")
    return {"grupo": grupo, "datos": datos}

@app.get(
    "/sensor/{sensor_name}/campos",
    tags=["Variables"],
    summary="Listar variables de interés",
    description="Obtiene las claves de campo registradas en los tópicos IMU, GPS y ENV durante el último día."
)
def listar_variables_interes(
    sensor_name: str,
    redis_client: redis.Redis = Depends(get_redis_client),
    query_api = Depends(get_influx_query_api)
):
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