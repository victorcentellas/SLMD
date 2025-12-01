from fastapi import FastAPI
from api.routes import sensors, consultas, topics  # <-- IMPORTANTE

app = FastAPI(title="API de Sensores", version="1.0.0")

app.include_router(sensors.router)
app.include_router(consultas.router)
app.include_router(topics.router)

