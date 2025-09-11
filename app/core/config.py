# core/config.py

import os

# ----------------------------
# Redis
# ----------------------------
REDIS_HOST = os.getenv("REDIS_HOST", "192.168.192.156")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))

# ----------------------------
# InfluxDB
# ----------------------------
INFLUXDB_URL = os.getenv("INFLUXDB_URL", "http://192.168.192.156:8086")
INFLUXDB_TOKEN = os.getenv(
    "INFLUXDB_TOKEN",
    "hQuGGvtteZvXhCdiTE_CcG1MCIOFe_D4o8HJUWonWKhOx2jyUqUsckGTJKeboN0hK83M1MWpjS-fvgyAWDw1hA=="
)
INFLUXDB_ORG = os.getenv("INFLUXDB_ORG", "UCLM")
INFLUXDB_BUCKET = os.getenv("INFLUXDB_BUCKET", "datos")

# ----------------------------
# EMQX API
# ----------------------------
EMQX_API = os.getenv("EMQX_API", "http://192.168.192.154:18083/api/v5")
EMQX_USER = os.getenv("EMQX_USER", "root")
EMQX_PASS = os.getenv("EMQX_PASS", "tfg-2425")
API_KEY = os.getenv("EMQX_API_KEY", "2af8512a8d99c1e0")
SECRET_KEY = os.getenv("EMQX_SECRET_KEY", "XsziTed3XXe9Bes1dU6vTX9ATASLwvYmz5IhcekOeRd8C")
TOKEN_BEARER = os.getenv(
    "EMQX_TOKEN_BEARER",
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJleHAiOjE3NTA0MTM3MTc1NjcsImlzcyI6IkVNUVgifQ.Bzc_m0gCNfV2RrYMbl1cWhkofYLP-D5HNumEGuTvHlA"
)

# ----------------------------
# Docker
# ----------------------------
DOCKER_HOST = os.getenv("DOCKER_HOST", "unix:///var/run/docker.sock")
DOCKER_GROUP_ID = int(os.getenv("DOCKER_GROUP_ID", 990))  # para agregar usuario al grupo docker
