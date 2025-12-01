from fastapi import APIRouter, Depends, HTTPException
from core.dependencies import get_redis_client, get_docker_client
from repositories.sensor_repository import SensorRepository
from services.sensor_service import SensorService
from models.sensor import SensorList, SensorCreateResponse, SensorActiveResponse, SensorInactiveResponse
import redis
import docker

router = APIRouter(prefix="/sensores", tags=["Sensores"])

def get_service(redis_client: redis.Redis = Depends(get_redis_client),
                docker_client: docker.DockerClient = Depends(get_docker_client)):
    repo = SensorRepository(redis_client)
    return SensorService(repo, docker_client)

@router.get("/", response_model=SensorList)
def listar_sensores(service: SensorService = Depends(get_service)):
    try:
        return {"sensores": service.list_sensors()}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.get("/activos", response_model=SensorActiveResponse)
def listar_sensores_activos(service: SensorService = Depends(get_service)):
    try:
        return {"sensores_activos": service.list_active_sensors()}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.get("/inactivos", response_model=SensorInactiveResponse)
def listar_sensores_inactivos(service: SensorService = Depends(get_service)):
    try:
        return {"sensores_inactivos": service.list_inactive_sensors()}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.post("/crear/{sensor_name}/{sensors}", response_model=SensorCreateResponse)
def crear_sensor(sensor_name: str, sensors: str, service: SensorService = Depends(get_service)):
    try:
        return service.create_sensor(sensor_name, sensors)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/vincular_sensor/{sensor_name}/")
def vincular_sensor(sensor_name: str, service: SensorService = Depends(get_service)):
    try:
        return service.vincular_sensor(sensor_name)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except LookupError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.delete("/desvincular/{sensor_name}")
def desvincular_sensor(sensor_name: str, service: SensorService = Depends(get_service)):
    try:
        return service.desvincular_sensor(sensor_name)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.post("/{sensor_name}/start")
def start_sensor(sensor_name: str, service: SensorService = Depends(get_service)):
    try:
        return service.start_sensor(sensor_name)
    except LookupError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{sensor_name}/stop")
def stop_sensor(sensor_name: str, service: SensorService = Depends(get_service)):
    try:
        return service.stop_sensor(sensor_name)
    except LookupError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/{sensor_name}",description="Recuerda borrar primero borrar los topics asociados al sensor.")
def eliminar_sensor(sensor_name: str, service: SensorService = Depends(get_service)):
    try:
        return service.delete_sensor(sensor_name)
    except LookupError as e:
        raise HTTPException(status_code=404, detail=str(e))