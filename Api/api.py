from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel
from typing import List, Dict, Any
from influxdb_client import InfluxDBClient, client
import redis
import docker
import uuid
import base64
import requests


# --------------------------------------------------
# Configuración (mantén estos valores según tu entorno)
# --------------------------------------------------
REDIS_HOST = "192.168.192.156"
REDIS_PORT = 6379

INFLUXDB_URL = "http://192.168.192.156:8086"
INFLUXDB_TOKEN = "hQuGGvtteZvXhCdiTE_CcG1MCIOFe_D4o8HJUWonWKhOx2jyUqUsckGTJKeboN0hK83M1MWpjS-fvgyAWDw1hA=="
INFLUXDB_ORG = "UCLM"
INFLUXDB_BUCKET = "datos"

EMQX_API = "http://192.168.192.154:18083/api/v5"
EMQX_USER = "root"
EMQX_PASS = "tfg-2425"

API_KEY = "2af8512a8d99c1e0"
SECRET_KEY="XsziTed3XXe9Bes1dU6vTX9ATASLwvYmz5IhcekOeRd8C"
Token_Bearer="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJleHAiOjE3NTA0MTM3MTc1NjcsImlzcyI6IkVNUVgifQ.Bzc_m0gCNfV2RrYMbl1cWhkofYLP-D5HNumEGuTvHlA"
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

# Helper para construir la clave en Redis
def get_topic_key(sensor_name: str, topic_type: str) -> str:
    return f"topic:{sensor_name}:{topic_type.upper()}"

def get_emqx_connection() -> requests.Session:
    session = requests.Session()
    creds = f"{API_KEY}:{SECRET_KEY}"
    token = base64.b64encode(creds.encode()).decode()
    session.headers.update({"Authorization": f"Basic {token}"})
    return session

def get_emqx_clients(page=1, node=None, limit=50, ip_address=None, fields="all"):
    session = get_emqx_connection()
    url = f"{EMQX_API}/clients"
    params = {
        "page": page,
        "limit": limit,
        "fields": fields
    }
    if node:
        params["node"] = node
    if ip_address:
        params["ip_address"] = ip_address
    
    response = session.get(url, params=params)
    response.raise_for_status()
    return response.json()

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

# Modelos para CRUD de topics
class Topic(BaseModel):
    sensor_name: str
    topic_type: str
    complete_topic: str  # Campo que incluye el topic completo

class Topics(BaseModel):
    sensor_name: str
    topics: List[Topic]

class TopicIn(BaseModel):
    sensor_name: str
    topic_type: str

def get_sensor_id_by_name(redis_client: redis.Redis, sensor_name: str) -> str:
    sensor_id = redis_client.get(f"sensor:{sensor_name}")
    if not sensor_id:
        raise HTTPException(status_code=404, detail="Sensor no encontrado")
    return sensor_id
# ---------------------
# Endpoints de Sensores
# ---------------------
@app.get("/sensores/", tags=["Sensores"], response_model=SensorList, summary="Listar todos los sensores")
def listar_sensores(redis_client: redis.Redis = Depends(get_redis_client)):
    sensor_keys = redis_client.keys("sensor:sensor*")
    if not sensor_keys:
        raise HTTPException(status_code=404, detail="No se encontraron sensores")
    sensores = []
    for key in sensor_keys:
        key_parts = key.split(":")
        tipo = key_parts[1]
        sensores.append(Sensor(tipo=tipo, sensor_id=redis_client.get(key)))
    return {"sensores": sensores}

@app.get("/sensores/activos", tags=["Sensores"], summary="Listar sensores activos")
def listar_sensores_activos(redis_client: redis.Redis = Depends(get_redis_client)):
    sensor_keys = redis_client.keys("sensor:sensor*")
    if not sensor_keys:
        raise HTTPException(status_code=404, detail="No se encontraron sensores")
        
    emqx_response_dummys = get_emqx_clients(page=1, node="emqx@172.18.0.2", ip_address="192.168.192.92")
    emqx_clients = emqx_response_dummys.get("data", [])    
    emqx_response_gateway = get_emqx_clients(page=1, node="emqx@172.18.0.2", ip_address="192.168.192.202")
    emqx_clients += emqx_response_gateway.get("data", [])
    # Se asume que el clientid retornado por EMQX es igual al valor de la clave id:sensor
    clientes_activos = {client.get("clientid") for client in emqx_clients}
    
    activos = []
    for key in sensor_keys:
        # El valor de la clave es el clientId asignado al sensor
        sensor_id = redis_client.get(key)
        sensor_name = key.split("id:")[-1]
        if sensor_id in clientes_activos:
            activos.append({
                "sensor": sensor_name,
                "sensor_id": sensor_id
            })
    
    if not activos:
        raise HTTPException(status_code=404, detail="No se encontraron sensores activos")
    return {"sensores_activos": activos}



@app.get("/sensores/inactivos", tags=["Sensores"], summary="Listar sensores inactivos")
def listar_sensores_inactivos(redis_client: redis.Redis = Depends(get_redis_client)):
    sensor_keys = redis_client.keys("sensor:sensor*")
    if not sensor_keys:
        raise HTTPException(status_code=404, detail="No se encontraron sensores")

    # Consulta a EMQX para obtener los clientes activos 
    emqx_response = get_emqx_clients(page=1, node="emqx@172.18.0.2", ip_address="192.168.192.92")
    emqx_clients = emqx_response.get("data", [])
    emqx_response = get_emqx_clients(page=1, node="emqx@172.18.0.2", ip_address="192.168.192.202")
    emqx_clients += emqx_response.get("data", [])

    # Se asume que el clientid retornado por EMQX es igual al valor de la clave id:sensor
    clientes_inactivos = {client.get("clientid") for client in emqx_clients}

    inactivos = []
    for key in sensor_keys:
        sensor_id = redis_client.get(key)
        sensor_name = key.split("id:")[-1]
        if sensor_id not in clientes_inactivos:
            inactivos.append({
                "sensor": sensor_name,
                "sensor_id": sensor_id
            })

    if not inactivos:
        raise HTTPException(status_code=404, detail="No se encontraron sensores inactivos")
    return {"sensores_inactivos": inactivos}

@app.post("/crear_sensor/{sensor_name}/{sensors}", tags=["Gestión de Sensores"], summary="Crear sensor")
def crear_sensor(sensor_name: str, sensors: str,
                 redis_client: redis.Redis = Depends(get_redis_client),
                 docker_client: docker.DockerClient = Depends(get_docker_client)):
    # Evita duplicados comprobando la existencia del sensor_name
    if redis_client.exists(f"sensor:{sensor_name}"):
        raise HTTPException(status_code=400, detail="El sensor ya existe")
    
    sensor_id = str(uuid.uuid4())[:8]
    
    try:
        container = docker_client.containers.run(
            "agente-sensor", 
            detach=True, 
            name=sensor_name, 
            network="emqx-network", 
            environment={"AGENT_NAME": sensor_name, "AGENT_ID": sensor_id, "SENSORS": sensors},
        )
        # Almacena la relación en dos claves:
        # Clave "id:<sensor_id>" → sensor_name
        # Clave "sensor:<sensor_name>" → sensor_id
        redis_client.set(f"id:{sensor_id}", sensor_name)
        redis_client.set(f"sensor:{sensor_name}", sensor_id)
        
        return {"message": f"Sensor {sensor_name} creado con éxito", "sensor_id": sensor_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))



@app.post("/vincular_sensor/{sensor_name}/", tags=["Gestión de Sensores"], summary="Vincular sensor")
def vincular_sensor(sensor_name: str, redis_client: redis.Redis = Depends(get_redis_client)):
    # Comprueba que el sensor no se haya vinculado previamente (por sensor_name)
    if redis_client.exists(f"sensor:{sensor_name}"):
        raise HTTPException(status_code=400, detail=f"El {sensor_name} ya existe")
    
    emqx_response = get_emqx_clients(page=1, node="emqx@172.18.0.2", ip_address="192.168.192.202")
    emqx_clients = emqx_response.get("data", [])
    sensor_keys = redis_client.keys("id:*")

    
    for client in emqx_clients:
        candidate = client.get("clientid", "").lower()
        print(f"Buscando vincular sensor {sensor_name} con clientid {candidate}")
        for key in sensor_keys:
            # Extrae el clientid de la clave, que es el valor después de "id:"
            key_parts = key.split(":")
            if len(key_parts) < 2:
                continue
        # Se asume que el clientid se iguala (ignorando mayúsculas) a sensor_name
            print(f"Comparando {candidate} con {key_parts[1].lower()}")
            if candidate == key_parts[1].lower():
                # Si la clave "id:{candidate}" ya existe, continúa con el siguiente
                if redis_client.exists(f"id:{candidate}"):
                    raise HTTPException(status_code=400, detail=f"El {candidate} ya existe")

            matched_client_id = candidate
            break
            
    if not matched_client_id:
        raise HTTPException(status_code=404, detail="No se encontró ningún clientid disponible para vincular")
    
    # Almacena la relación en Redis utilizando el client id real
    redis_client.set(f"id:{matched_client_id}", sensor_name)
    redis_client.set(f"sensor:{sensor_name}", matched_client_id)
    
    return {"message": f"Sensor {sensor_name} vinculado exitosamente", "sensor_id": matched_client_id}

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
    # Obtiene sensor_id usando la clave "sensor:<sensor_name>"
    sensor_id = get_sensor_id_by_name(redis_client, sensor_name)
    
    try:
        container = docker_client.containers.get(sensor_name)
        container.remove(force=True)
        # Elimina ambas claves para mantener la unicidad
        redis_client.delete(f"sensor:{sensor_name}")
        redis_client.delete(f"id:{sensor_id}")
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
    description="Consulta una variable publicada en los tópicos: IMU, GPS o ENV"
)
def obtener_variable(
    sensor_name: str,
    var_name: str,
    start: str,
    stop: str,
    redis_client: redis.Redis = Depends(get_redis_client),
    query_api = Depends(get_influx_query_api)
):
    # Obtiene el sensor_id a partir del sensor_name
    sensor_id = get_sensor_id_by_name(redis_client, sensor_name)
    if not sensor_id:
        raise HTTPException(status_code=404, detail="Sensor no encontrado")
    # Recupera el set de topics asociados al sensor
    topics_available = redis_client.smembers(sensor_id)
    if not topics_available:
        raise HTTPException(status_code=404, detail="No se encontraron topics para este sensor")
    
    # Construye la condición de filtro uniendo todos los topics disponibles
    filter_conditions = " or ".join([f'r.topic == "{topic}"' for topic in topics_available])
    
    query = f'''
        from(bucket: "{INFLUXDB_BUCKET}")
            |> range(start: {start}, stop: {stop})
            |> filter(fn: (r) => {filter_conditions})
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
    sensor_id = get_sensor_id_by_name(redis_client, sensor_name)
    if not sensor_id:
        raise HTTPException(status_code=404, detail="Sensor no encontrado")
    tipo_sensor = tipo_sensor.upper()
    if tipo_sensor not in ["IMU", "GPS", "ENV"]:
        raise HTTPException(status_code=400, detail="Tipo de sensor inválido. Use 'IMU', 'GPS' o 'ENV'")
    
    # Verifica que el topic correspondiente exista en Redis
    complete_topic = f"Si/{sensor_id}/{tipo_sensor}"
    if not redis_client.sismember(sensor_id, complete_topic):
        raise HTTPException(status_code=404, detail=f"El topic {complete_topic} no se encontró en la base de datos")
    
    query = f'''
        from(bucket: "{INFLUXDB_BUCKET}")
            |> range(start: {start}, stop: {stop})
            |> filter(fn: (r) => r.topic == "{complete_topic}")
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
    sensor_id = get_sensor_id_by_name(redis_client, sensor_name)
    if not sensor_id:
        raise HTTPException(status_code=404, detail="Sensor no encontrado")
    # Recupera todos los topics asociados al sensor
    topics_available = redis_client.smembers(sensor_id)
    if not topics_available:
        raise HTTPException(status_code=404, detail="No se encontraron topics para este sensor")
    
    # Filtrar aquellos topics que sean del tipo "IMU"
    imu_topics = [topic for topic in topics_available if topic.endswith("/IMU")]
    if not imu_topics:
        raise HTTPException(status_code=404, detail="No se encontró topic de tipo IMU para este sensor")
    
    # Si hay más de un topic IMU, genera una condición OR para cada uno
    filter_condition = " or ".join([f'r.topic == "{topic}"' for topic in imu_topics])
    
    query = f'''
        import "strings"
        from(bucket: "{INFLUXDB_BUCKET}")
            |> range(start: {start}, stop: {stop})
            |> filter(fn: (r) => {filter_condition})
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
    sensor_id = get_sensor_id_by_name(redis_client, sensor_name)
    if not sensor_id:
        raise HTTPException(status_code=404, detail="Sensor no encontrado")
    topics_set = redis_client.smembers(sensor_id)
    if not topics_set:
        raise HTTPException(status_code=404, detail="No se encontraron topics para este sensor")
    
    
    filter_condition = " or ".join([f'r.topic == "{topic}"' for topic in topics_set])

    query = f'''
        import "influxdata/influxdb/schema"
        schema.fieldKeys(
            bucket: "{INFLUXDB_BUCKET}",
            predicate: (r) => {filter_condition},
            start: -1d
        )
    '''
    print(f"Ejecutando consulta para listar variables de interés: {query}")
    result = query_api.query(query, org=INFLUXDB_ORG)
    variables = [record.get_value() for table in result for record in table.records]
    if not variables:
        raise HTTPException(status_code=404, detail="No se encontraron variables de interés")
    return {"variables": variables}

# --------------------------
# Endpoints de Topics
# --------------------------

@app.post("/topic/{sensor_name}/{topics}", tags=["Topics"], summary="Crear topic")
def crear_topic(sensor_name: str, topics: str, redis_client: redis.Redis = Depends(get_redis_client)):
    # Recupera el identificador real del sensor (UUID de 8 dígitos) desde Redis
    sensor_id = get_sensor_id_by_name(redis_client, sensor_name)
    if not sensor_id:
        raise HTTPException(status_code=404, detail="Sensor no encontrado")
    # Aquí usaremos el sensor_id (por ejemplo, "c0ae15ea") como clave de un set en Redis
    topic_types = [tt.strip().upper() for tt in topics.split(",")]
    created_topics = {}
    errors = []
    for ttype in topic_types:
        complete_topic = f"Si/{sensor_id}/{ttype}"
        # Si ya existe el topic en el set, lanza error
        if redis_client.sismember(sensor_id, complete_topic):
            errors.append(f"El topic para {ttype} ya existe")
            continue
        redis_client.sadd(sensor_id, complete_topic)
        created_topics[ttype] = complete_topic
    if not created_topics:
        raise HTTPException(status_code=400, detail="No se crearon topics: " + ", ".join(errors))
    return {"message": "Topic(s) creado(s) con éxito", "topics": created_topics, "errors": errors}
    
# Listar todos los topics
@app.get("/topic/{sensor_name}/{topic_type}", tags=["Topics"], response_model=Topic, summary="Obtener topic")
def obtener_topic(sensor_name: str, topic_type: str, redis_client: redis.Redis = Depends(get_redis_client)):
    sensor_id = get_sensor_id_by_name(redis_client, sensor_name)
    if not sensor_id:
        raise HTTPException(status_code=404, detail="Sensor no encontrado")
    # Construir el topic completo según el formato usado en la creación
    complete_topic = f"Si/{sensor_id}/{topic_type.upper()}"
    if not redis_client.sismember(sensor_id, complete_topic):
        raise HTTPException(status_code=404, detail="Topic no encontrado")
    # Retorna el topic construido; si deseas usar un modelo, asegúrate de que Topic acepte estos campos
    return Topic(sensor_name=sensor_name, topic_type=topic_type.upper(), complete_topic=complete_topic)

# Obtener todos los topics asociados a un sensor

@app.get("/topics/{sensor_name}", tags=["Topics"], response_model=Topics, summary="Obtener topics por sensor")
def obtener_topics_por_sensor(sensor_name: str, redis_client: redis.Redis = Depends(get_redis_client)):
    sensor_id = get_sensor_id_by_name(redis_client, sensor_name)
    if not sensor_id:
        raise HTTPException(status_code=404, detail="Sensor no encontrado")
    topics_set = redis_client.smembers(sensor_id)
    if not topics_set:
        raise HTTPException(status_code=404, detail="No se encontraron topics para este sensor")
    topics_list = []
    for topic in topics_set:
        # Se espera el formato "Si/{sensor_id}/{topic_type}"
        parts = topic.split("/")
        topic_type = parts[-1] if len(parts) >= 3 else ""
        topics_list.append(Topic(sensor_name=sensor_name, topic_type=topic_type, complete_topic=topic))
    return {"sensor_name": sensor_name, "topics": topics_list}

# Eliminar todos los topics asociados a un sensor
@app.delete("/topics/{sensor_name}", tags=["Topics"], summary="Eliminar topics por sensor")
def eliminar_topics_por_sensor(sensor_name: str, redis_client: redis.Redis = Depends(get_redis_client)):
    sensor_id = get_sensor_id_by_name(redis_client, sensor_name)
    if not sensor_id:
        raise HTTPException(status_code=404, detail="Sensor no encontrado")
    topics_set = redis_client.smembers(sensor_id)
    if not topics_set:
        raise HTTPException(status_code=404, detail="No se encontraron topics para este sensor")
    # Elimina el set completo que almacena los topics para ese sensor
    redis_client.delete(sensor_id)
    return {"message": "Topics eliminados con éxito"}


# Eliminar topic en particular de un sensor

@app.delete("/topic/{sensor_name}/{topic_type}", tags=["Topics"], summary="Eliminar topic")
def eliminar_topic(sensor_name: str, topic_type: str, redis_client: redis.Redis = Depends(get_redis_client)):
    sensor_id = get_sensor_id_by_name(redis_client, sensor_name)
    if not sensor_id:
        raise HTTPException(status_code=404, detail="Sensor no encontrado")
    complete_topic = f"Si/{sensor_id}/{topic_type.upper()}"
    if not redis_client.sismember(sensor_id, complete_topic):
        raise HTTPException(status_code=404, detail="Topic no encontrado")
    redis_client.srem(sensor_id, complete_topic)
    return {"message": "Topic eliminado con éxito"}