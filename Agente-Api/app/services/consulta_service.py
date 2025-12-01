from services.sensor_service import SensorService
from services.topic_service import TopicService
from core.config import INFLUXDB_BUCKET, INFLUXDB_ORG

class ConsultaService:
    def __init__(self, sensor_service: SensorService, topic_service: TopicService, query_api):
        self.sensor_service = sensor_service
        self.topic_service = topic_service
        self.query_api = query_api

    def obtener_variable(self, sensor_name, var_name, start, stop):
        topics = self.topic_service.listar_topics_sensor(sensor_name)
        if not topics:
            raise ValueError("No se encontraron topics para este sensor")

        filter_conditions = " or ".join([f'r.topic == "{topic}"' for topic in topics])
        query = f'''
            from(bucket: "{INFLUXDB_BUCKET}")
                |> range(start: {start}, stop: {stop})
                |> filter(fn: (r) => {filter_conditions})
                |> filter(fn: (r) => r._field == "{var_name}")
                |> yield(name: "last")
        '''
        result = self.query_api.query(query, org=INFLUXDB_ORG)
        datos = [{"value": r.get_value(), "timestamp": r.get_time().isoformat()} 
                 for table in result for r in table.records]
        if not datos:
            raise LookupError(f"No se encontraron datos para la variable {var_name}")
        return {"variable": var_name, "datos": datos}

    def obtener_medidas_grupo_por_tipo(self, sensor_name, tipo_sensor, start, stop):
        sensor_id = self.sensor_service.get_sensor_id(sensor_name)
        if not sensor_id:
            raise LookupError("Sensor no encontrado")

        tipo_sensor = tipo_sensor.upper()
        if tipo_sensor not in ["IMU", "GPS", "ENV"]:
            raise ValueError("Tipo de sensor inválido")

        if not self.topic_service.topic_exists(sensor_id, tipo_sensor):
            raise LookupError(f"El topic Si/{sensor_id}/{tipo_sensor} no se encontró")
        complete_topic = f"Si/{sensor_id}/{tipo_sensor}"

        query = f'''
            from(bucket: "{INFLUXDB_BUCKET}")
                |> range(start: {start}, stop: {stop})
                |> filter(fn: (r) => r.topic == "{complete_topic}")
                |> aggregateWindow(every: 1s, fn: last, createEmpty: false)
                |> pivot(rowKey: ["_time"], columnKey: ["_field"], valueColumn: "_value")
                |> yield(name: "last")
        '''
        result = self.query_api.query(query, org=INFLUXDB_ORG)
        datos = [{"timestamp": r.get_time().isoformat(),
                  "values": {k: r.values[k] for k in r.values if k not in ["_time","result","table","_start","_stop","_measurement","host","topic"]}}
                 for table in result for r in table.records]
        if not datos:
            raise LookupError(f"No se encontraron registros para el grupo {tipo_sensor}")
        return {"grupo": tipo_sensor, "datos": datos}

    def obtener_medidas_grupo(self, sensor_name, grupo, start, stop):
        topics_available = self.topic_service.listar_topics_sensor(sensor_name)
        if not topics_available:
            raise ValueError("No se encontraron topics para este sensor")

        imu_topics = [t.decode() if isinstance(t, bytes) else t for t in topics_available if str(t).endswith("/IMU")]
        if not imu_topics:
            raise LookupError("No se encontró topic de tipo IMU para este sensor")

        filter_condition = " or ".join([f'r.topic == "{topic}"' for topic in imu_topics])

        query = f'''
            import "strings"
            from(bucket: "{INFLUXDB_BUCKET}")
                |> range(start: {start}, stop: {stop})
                |> filter(fn: (r) => {filter_condition})
                |> filter(fn: (r) => strings.containsStr(v: r._field, substr: "{grupo}"))
                |> aggregateWindow(every: 1s, fn: last, createEmpty: false)
                |> pivot(rowKey: ["_time"], columnKey: ["_field"], valueColumn: "_value")
                |> yield(name: "last")
        '''

        result = self.query_api.query(query, org=INFLUXDB_ORG)

        datos = []
        for table in result:
            for record in table.records:
                values = {
                    key: record.values[key]
                    for key in record.values
                    if key not in [
                        "_time", "result", "table", "_start", "_stop",
                        "_measurement", "host", "topic"
                    ]
                }
                datos.append({
                    "timestamp": record.get_time().isoformat(),
                    "values": values
                })

        if not datos:
            raise LookupError(f"No se encontraron registros para el grupo {grupo}")

        return {"grupo": grupo, "datos": datos}

    def listar_variables_interes(self, sensor_name):
        topics = self.topic_service.listar_topics_sensor(sensor_name)
        if not topics:
            raise ValueError("No se encontraron topics para este sensor")

        filter_condition = " or ".join([f'r.topic == "{topic}"' for topic in topics])
        query = f'''
            import "influxdata/influxdb/schema"
            schema.fieldKeys(
                bucket: "{INFLUXDB_BUCKET}",
                predicate: (r) => {filter_condition},
                start: -1d
            )
        '''
        result = self.query_api.query(query, org=INFLUXDB_ORG)
        variables = [r.get_value() for table in result for r in table.records]
        if not variables:
            raise LookupError("No se encontraron variables de interés")
        return {"variables": variables}