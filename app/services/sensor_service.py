import uuid
import docker
from repositories.sensor_repository import SensorRepository
from core.dependencies import get_emqx_clients

class SensorService:
    def __init__(self, repo: SensorRepository, docker_client: docker.DockerClient):
        self.repo = repo
        self.docker = docker_client

    def get_sensor_id(self, sensor_name: str):
        return self.repo.get_sensor_id(sensor_name)

    def list_sensors(self):
        keys = self.repo.get_all_sensors()
        if not keys:
            raise ValueError("No se encontraron sensores")
        return [{"sensor": k.split(":")[1], "sensor_id": self.repo.redis.get(k)} for k in keys]

    def list_active_sensors(self):
        keys = self.repo.get_all_sensors()
        if not keys:
            raise ValueError("No se encontraron sensores")
        emqx_clients = get_emqx_clients(page=1, ip_address="192.168.192.92")["data"]
        emqx_clients += get_emqx_clients(page=1, ip_address="192.168.192.202")["data"]
        clientes_activos = {c.get("clientid") for c in emqx_clients}
        activos = [{"sensor": k.split(":")[1], "sensor_id": self.repo.redis.get(k)}
                   for k in keys if self.repo.redis.get(k) in clientes_activos]
        if not activos:
            raise ValueError("No se encontraron sensores activos")
        return activos

    def list_inactive_sensors(self):
        keys = self.repo.get_all_sensors()
        if not keys:
            raise ValueError("No se encontraron sensores")
        emqx_clients = get_emqx_clients(page=1, ip_address="192.168.192.92")["data"]
        emqx_clients += get_emqx_clients(page=1, ip_address="192.168.192.202")["data"]
        clientes_activos = {c.get("clientid") for c in emqx_clients}
        inactivos = [{"sensor": k.split(":")[1], "sensor_id": self.repo.redis.get(k)}
                     for k in keys if self.repo.redis.get(k) not in clientes_activos]
        if not inactivos:
            raise ValueError("No se encontraron sensores inactivos")
        return inactivos

    def create_sensor(self, sensor_name: str, sensors: str):
        if self.repo.sensor_exists(sensor_name):
            raise ValueError("El sensor ya existe")
        sensor_id = str(uuid.uuid4())[:8]
        container = None
        try:
            container = self.docker.containers.run(
                "agente-sensor", detach=True, name=sensor_name,
                network="emqx-network",
                environment={"AGENT_NAME": sensor_name, "AGENT_ID": sensor_id, "SENSORS": sensors},
            )
            self.repo.save_sensor(sensor_name, sensor_id)
            return {"message": f"Sensor {sensor_name} creado con éxito", "sensor_id": sensor_id}
        except Exception as e:
            if container:
                try:
                    container.remove(force=True)
                except Exception:
                    pass
            raise RuntimeError(f"Error creando sensor {sensor_name}: {e}")


    def vincular_sensor(self, sensor_name: str):
                # Obtén los clientids de EMQX
        emqx_response = get_emqx_clients(page=1, node="emqx@172.18.0.2", ip_address="192.168.192.202")
        emqx_clients = emqx_response.get("data", [])
        client_ids = [client.get("clientid", "").lower() for client in emqx_clients if client.get("clientid")]

        matched_client_id = self.repo.find_and_link_sensor(sensor_name, client_ids)
        if not matched_client_id:
            raise LookupError("No se encontró ningún clientid disponible para vincular")

        return {"message": f"Sensor {sensor_name} vinculado exitosamente", "sensor_id": matched_client_id}

    def desvincular_sensor(self, sensor_name: str):
        if not self.repo.sensor_exists(sensor_name):
            raise ValueError(f"Sensor {sensor_name} no vinculado")
        sensor_id = self.repo.delete_sensor_link(sensor_name)
        return {"message": f"Sensor {sensor_name} desvinculado exitosamente", "sensor_id": sensor_id}

    def start_sensor(self, sensor_name: str):
        try:
            container = self.docker.containers.get(sensor_name)
            container.start()
            return {"message": f"Sensor {sensor_name} iniciado."}
        except docker.errors.NotFound:
            raise LookupError("Sensor no encontrado")
        except Exception as e:
            raise RuntimeError(str(e))

    def stop_sensor(self, sensor_name: str):
        try:
            container = self.docker.containers.get(sensor_name)
            container.stop()
            return {"message": f"Sensor {sensor_name} detenido."}
        except docker.errors.NotFound:
            raise LookupError("Sensor no encontrado")
        except Exception as e:
            raise RuntimeError(str(e))

    def delete_sensor(self, sensor_name: str):
        sensor_id = self.repo.get_sensor_id(sensor_name)
        if not sensor_id:
            raise LookupError("Sensor no encontrado")
        try:
            container = self.docker.containers.get(sensor_name)
            container.remove(force=True)
        except docker.errors.NotFound:
            pass
        self.repo.delete_sensor(sensor_name, sensor_id)
        return {"message": f"Sensor {sensor_name} eliminado."}