import redis

class SensorRepository:
    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client

    def get_all_sensors(self):
        return [self._decode(k) for k in self.redis.keys("sensor:sensor*")]

    def get_sensor_id(self, sensor_name: str) -> str:
        sensor_id = self.redis.get(f"sensor:{sensor_name}")
        return self._decode(sensor_id) if sensor_id else None

    def save_sensor(self, sensor_name: str, sensor_id: str):
        self.redis.set(f"id:{sensor_id}", sensor_name)
        self.redis.set(f"sensor:{sensor_name}", sensor_id)

    def delete_sensor(self, sensor_name: str ,sensor_id: str):
            self.redis.delete(f"sensor:{sensor_name}")
            self.redis.delete(f"id:{sensor_id}")

    def sensor_exists(self, sensor_name: str) -> bool:
        return self.redis.exists(f"sensor:{sensor_name}") > 0

    def vincular_sensor(self, client_ids: list[str]):
        # Solo devuelve un id disponible, sin lanzar HTTPException
        for candidate in client_ids:
            if not self.redis.exists(f"id:{candidate}"):
                return candidate
        return None
    def delete_sensor_link(self, sensor_name: str):
        sensor_id = self.get_sensor_id(sensor_name)
        self.redis.delete(f"sensor:{sensor_name}")
        self.redis.delete(f"id:{sensor_id}")
        return sensor_id

    def _decode(self, value):
        if isinstance(value, bytes):
            return value.decode()
        return value
