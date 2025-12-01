from pydantic import BaseModel
from typing import List

class Topic(BaseModel):
    sensor_id: str
    sensor_name: str
    topic_type: str
    complete_topic: str

class Topics(BaseModel):
    sensor_name: str
    topics: List[Topic]
