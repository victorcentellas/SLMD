from fastapi import APIRouter, Depends, HTTPException
from typing import List
from core.dependencies import get_redis_client, get_docker_client
from models.topic import Topic, Topics
from repositories.topic_repository import TopicRepository
from services.sensor_service import SensorService
from services.topic_service import TopicService
from repositories.sensor_repository import SensorRepository
import redis
import docker

router = APIRouter(prefix="/topics", tags=["Topics"])

def get_topic_service(
    redis_client: redis.Redis = Depends(get_redis_client),
    docker_client: docker.DockerClient = Depends(get_docker_client)
) -> TopicService:
    sensor_repo = SensorRepository(redis_client)
    sensor_service = SensorService(sensor_repo, docker_client)  
    topic_repo = TopicRepository(redis_client)
    return TopicService(sensor_service, topic_repo)

@router.post("/{sensor_name}", summary="Crear topics")
def crear_topic(
    sensor_name: str,
    topics: str,
    service: TopicService = Depends(get_topic_service)
):
    topic_list = [t.strip().upper() for t in topics.split(",")]
    try:
        created, errors = service.crear_topics(sensor_name, topic_list)
        return {"message": "Topic(s) creado(s) con éxito", "topics": created, "errors": errors}
    except LookupError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/{sensor_name}", response_model=Topics, summary="Obtener todos los topics de un sensor")
def listar_topics_sensor(
    sensor_name: str,
    service: TopicService = Depends(get_topic_service)
):
    try:
        topics_set = service.listar_topics_sensor(sensor_name)
        sensor_id = service.sensor_service.get_sensor_id(sensor_name)
        topics_list = [
            Topic(
                sensor_id=sensor_id,
                sensor_name=sensor_name,
                topic_type=t.split("/")[-1],
                complete_topic=t
            )
            for t in topics_set
        ]
        return {"sensor_name": sensor_name, "topics": topics_list}
    except LookupError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.get("/", response_model=List[Topics], summary="Obtener todos los topics")
def listar_topics(service: TopicService = Depends(get_topic_service)):
    all_topics = service.listar_topics()
    result = []
    for sensor_name, topics_set in all_topics.items():
        sensor_id = service.sensor_service.get_sensor_id(sensor_name)
        topics_list = [
            Topic(
                sensor_id=sensor_id,
                sensor_name=sensor_name,
                topic_type=t.split("/")[-1],
                complete_topic=t
            )
            for t in topics_set
        ]
        result.append(Topics(sensor_name=sensor_name, topics=topics_list))
    return result

@router.delete("/{sensor_name}", summary="Eliminar todos los topics")
def eliminar_todos_topics(
    sensor_name: str,
    service: TopicService = Depends(get_topic_service)
):
    try:
        service.eliminar_todos_topics(sensor_name)
        return {"message": "Topics eliminados con éxito"}
    except LookupError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.delete("/{sensor_name}/{topic_type}", summary="Eliminar un topic")
def eliminar_topic(
    sensor_name: str,
    topic_type: str,
    service: TopicService = Depends(get_topic_service)
):
    try:
        service.eliminar_topic(sensor_name, topic_type)
        return {"message": "Topic eliminado con éxito"}
    except LookupError as e:
        raise HTTPException(status_code=404, detail=str(e))