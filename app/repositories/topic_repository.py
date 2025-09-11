import redis
from typing import List

class TopicRepository:
    def __init__(self, redis_client: redis.Redis):
        self.redis_client = redis_client

    def _decode(self, value):
        if isinstance(value, bytes):
            return value.decode()
        return value
    def topic_exists(self, sensor_id: str, topic_type: str) -> bool:
        complete_topic = f"Si/{sensor_id}/{topic_type.upper()}"
        return complete_topic in self.get_topics(sensor_id)

    def get_topics(self, sensor_id: str) -> List[str]:
        topics_set = self.redis_client.smembers(sensor_id)
        return [self._decode(t) for t in topics_set] if topics_set else []

    def get_all_topics(self) -> dict[str, list[str]]:
        sensor_keys = self.redis_client.keys("sensor:sensor*")
        if not sensor_keys:
            return {}

        all_topics = {}
        for key in sensor_keys:
            sensor_name = key.decode() if isinstance(key, bytes) else key
            sensor_name = sensor_name.split(":")[1]

            sensor_id = self.redis_client.get(f"sensor:{sensor_name}")
            if not sensor_id:
                continue
            sensor_id = sensor_id.decode() if isinstance(sensor_id, bytes) else sensor_id

            topics_set = self.get_topics(sensor_id)
            topics_list = [t.decode() if isinstance(t, bytes) else t for t in topics_set]

            all_topics[sensor_name] = topics_list   # 👈 clave = sensor_name

        return all_topics

    def add_topic(self, sensor_id: str, topic_type: str) -> str:
        complete_topic = f"Si/{sensor_id}/{topic_type.upper()}"
        self.redis_client.sadd(sensor_id, complete_topic)
        return complete_topic

    def remove_topic(self, sensor_id: str, topic_type: str):
        
        complete_topic = f"Si/{sensor_id}/{topic_type.upper()}"
        self.redis_client.srem(sensor_id, complete_topic)

    def delete_all_topics(self, sensor_id: str):
        self.redis_client.delete(sensor_id)
