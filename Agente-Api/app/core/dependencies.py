import redis
import docker
from fastapi import Depends
from influxdb_client import InfluxDBClient
import requests
import base64
from core.config import REDIS_HOST, REDIS_PORT, INFLUXDB_URL, INFLUXDB_TOKEN, EMQX_API, API_KEY, SECRET_KEY

def get_redis_client() -> redis.Redis:
    return redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)

def get_docker_client() -> docker.DockerClient:
    return docker.from_env()

def get_influx_query_api():
    influx_client = InfluxDBClient(url=INFLUXDB_URL, token=INFLUXDB_TOKEN)
    return influx_client.query_api()

def get_emqx_connection() -> requests.Session:
    session = requests.Session()
    creds = f"{API_KEY}:{SECRET_KEY}"
    token = base64.b64encode(creds.encode()).decode()
    session.headers.update({"Authorization": f"Basic {token}"})
    return session

def get_emqx_clients(page=1, node=None, limit=50, ip_address=None, fields="all"):
    session = get_emqx_connection()
    url = f"{EMQX_API}/clients"
    params = {"page": page, "limit": limit, "fields": fields}
    if node:
        params["node"] = node
    if ip_address:
        params["ip_address"] = ip_address
    response = session.get(url, params=params)
    response.raise_for_status()
    return response.json()
