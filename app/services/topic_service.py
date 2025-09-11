from fastapi import HTTPException
from repositories.topic_repository import TopicRepository
from services.sensor_service import SensorService

class TopicService:
    def __init__(self, sensor_service: SensorService, topic_repo: TopicRepository):
        self.topic_repo = topic_repo
        self.sensor_service = sensor_service
    
    def topic_exists(self, sensor_id: str, topic_type:str) -> bool:
        return self.topic_repo.topic_exists(sensor_id,topic_type)
        

    def crear_topics(self, sensor_name: str, topic_types: list[str]):
        sensor_id = self.sensor_service.get_sensor_id(sensor_name)
        if not sensor_id:
            raise HTTPException(status_code=404, detail=f"Sensor {sensor_name} no encontrado")
        created_topics = {}
        errors = []
        for ttype in topic_types:
            try:
                complete_topic = self.topic_repo.add_topic(sensor_id, ttype)
                created_topics[ttype] = complete_topic
            except Exception as e:
                errors.append(str(e))
        if not created_topics:
            raise Exception("No se crearon topics: " + ", ".join(errors))
        return created_topics, errors

    def eliminar_topic(self, sensor_name: str, topic_type: str):
        sensor_id = self.sensor_service.get_sensor_id(sensor_name)
        if not sensor_id:
            raise HTTPException(status_code=404, detail=f"Sensor {sensor_name} no encontrado")
        self.topic_repo.remove_topic(sensor_id, topic_type)

    def listar_topics_sensor(self, sensor_name: str):
        sensor_id = self.sensor_service.get_sensor_id(sensor_name)
        if not sensor_id:
            raise HTTPException(status_code=404, detail=f"Sensor {sensor_name} no encontrado")
        topics = self.topic_repo.get_topics(sensor_id)
        return topics

    def listar_topics(self) -> dict[str, list[str]]:
        # Aquí no hace falta decodificar, ya lo hace el repo
        return self.topic_repo.get_all_topics()

    def eliminar_todos_topics(self, sensor_name: str):
        sensor_id = self.sensor_service.get_sensor_id(sensor_name)
        if not sensor_id:
            raise HTTPException(status_code=404, detail=f"Sensor {sensor_name} no encontrado")
        self.topic_repo.delete_all_topics(sensor_id)
