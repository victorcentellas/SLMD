from fastapi import APIRouter, Depends, HTTPException
from core.dependencies import get_redis_client, get_influx_query_api, get_docker_client
from services.consulta_service import ConsultaService
from services.sensor_service import SensorService
from services.topic_service import TopicService
from repositories.topic_repository import TopicRepository
from repositories.sensor_repository import SensorRepository
from models.consulta import VariableResponse, GrupoResponse, VariablesInteresResponse
from influxdb_client.client.query_api import QueryApi
import redis
import docker

router = APIRouter(prefix="/consultas", tags=["Consultas"])

def get_consulta_service(
    redis_client: redis.Redis = Depends(get_redis_client),
    query_api: QueryApi = Depends(get_influx_query_api),
    docker_client: docker.DockerClient = Depends(get_docker_client)
) -> ConsultaService:
    sensor_repo = SensorRepository(redis_client)
    sensor_service = SensorService(sensor_repo, docker_client)
    topic_repo = TopicRepository(redis_client)
    topic_service = TopicService(sensor_service, topic_repo)
    return ConsultaService(sensor_service, topic_service, query_api)

@router.get(
    "/sensor/{sensor_name}/variable/{var_name}/{start}/{stop}", 
    response_model=VariableResponse
)
def obtener_variable(
    sensor_name: str, 
    var_name: str, 
    start: str, 
    stop: str,
    service: ConsultaService = Depends(get_consulta_service)
):
    try:
        return service.obtener_variable(sensor_name, var_name, start, stop)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except LookupError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.get(
    "/sensor/{sensor_name}/grupo/{tipo_sensor}/{start}/{stop}", 
    response_model=GrupoResponse
)
def obtener_medidas_grupo_por_tipo(
    sensor_name: str, 
    tipo_sensor: str, 
    start: str, 
    stop: str,
    service: ConsultaService = Depends(get_consulta_service)
):
    try:
        return service.obtener_medidas_grupo_por_tipo(sensor_name, tipo_sensor, start, stop)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except LookupError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.get(
    "/sensor/{sensor_name}/grupo_medidas/{grupo}/{start}/{stop}",
    response_model=GrupoResponse,
    summary="Obtener grupo de medidas por intervalo",
    description="Agrupa registros de la métrica IMU que contienen el patrón indicado (por ejemplo, 'data_accelerometer_') y devuelve una fila por ventana."
)
def obtener_medidas_grupo(
    sensor_name: str,
    grupo: str,
    start: str,
    stop: str,
    service: ConsultaService = Depends(get_consulta_service)
):
    try:
        return service.obtener_medidas_grupo(sensor_name, grupo, start, stop)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except LookupError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.get(
    "/sensor/{sensor_name}/campos", 
    response_model=VariablesInteresResponse
)
def listar_variables_interes(
    sensor_name: str,
    service: ConsultaService = Depends(get_consulta_service)
):
    try:
        return service.listar_variables_interes(sensor_name)
    except LookupError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))