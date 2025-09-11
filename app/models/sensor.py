from pydantic import BaseModel
from typing import List, Dict, Any

class Sensor(BaseModel):
    sensor: str
    sensor_id: str

class SensorList(BaseModel):
    sensores: List[Sensor]

class SensorCreateResponse(BaseModel):
    message: str
    sensor_id: str

class SensorActiveResponse(BaseModel):
    sensores_activos: List[Sensor]

class SensorInactiveResponse(BaseModel):
    sensores_inactivos: List[Sensor]
