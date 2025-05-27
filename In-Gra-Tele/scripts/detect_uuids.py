#!/usr/bin/env python3

import uuid
import os
import json
import time
import re
from influxdb_client import InfluxDBClient

INFLUXDB_URL = "http://192.168.192.156:8086"
INFLUXDB_TOKEN = "hQuGGvtteZvXhCdiTE_CcG1MCIOFe_D4o8HJUWonWKhOx2jyUqUsckGTJKeboN0hK83M1MWpjS-fvgyAWDw1hA=="
INFLUXDB_ORG = "UCLM"
INFLUXDB_BUCKET = "datos"
DASHBOARD_PATH = "./grafana/dashboards"

def get_uuids():
    try:
        client = InfluxDBClient(url=INFLUXDB_URL, token=INFLUXDB_TOKEN, org=INFLUXDB_ORG)
        # Filtra para detectar topics de los 3 tipos de sensores.
        query = f'''
        from(bucket: "{INFLUXDB_BUCKET}")
          |> range(start: -3h)
          |> filter(fn: (r) => r["topic"] =~ /Si\\/([a-z0-9-]+)\\/(IMU)/)
          |> keep(columns: ["topic"])
          |> distinct(column: "topic")
        '''
        result = client.query_api().query(query)
        
        uuids = []
        # Se extrae el UUID (segundo elemento en el topic)
        for table in result:
            for record in table.records:
                uuid_valor = record.values.get("topic").split("/")[1]
                uuids.append(uuid_valor)
        print(f"UUIDs encontrados: {uuids}")
        return uuids
    except Exception as e:
        print(f" Error general: {e}")
        return []

def create_dashboard(uuid):
    # Mapeo para cada sensor: panel (agrupación de métricas) -> lista de _fields
    dashboard_panels_map = {
        "IMU": {
            "Accelerometer": ["accelerometer_x", "accelerometer_y", "accelerometer_z"],
            "Gyroscope": ["gyroscope_x", "gyroscope_y", "gyroscope_z"],
            "Magnetometer": ["magnetometer_x", "magnetometer_y", "magnetometer_z"],
            "Quaternion": ["quaternion_w", "quaternion_x", "quaternion_y", "quaternion_z"]
        },
        "GPS": {
            "GPS": ["latitud", "longitud", "altitud", "speed", "satellites", "hdop"]
        },
        "ENV": {
            "Environment": ["temperature", "pressure", "humidity"]
        }
    }
    
    # Dashboard base
    dashboard = {
        "annotations": {
            "list": [
                {
                    "builtIn": 1,
                    "datasource": {
                        "type": "datasource",
                        "uid": "grafana"
                    },
                    "enable": True,
                    "hide": True,
                    "iconColor": "rgba(0, 211, 255, 1)",
                    "name": "Annotations & Alerts",
                    "target": {
                        "limit": 100,
                        "matchAny": False,
                        "tags": [],
                        "type": "dashboard"
                    },
                    "type": "dashboard"
                }
            ]
        },
        "editable": True,
        "fiscalYearStartMonth": 0,
        "graphTooltip": 0,
        "id": 1,
        "links": [],
        "liveNow": False,
        "refresh": "5s",
        "schemaVersion": 39,
        "tags": [],
        "templating": {
            "list": []
        },
        "time": {
            "from": "now-30m",
            "to": "now"
        },
        "timepicker": {},
        "timezone": "",
        "title": f"Dashboard {uuid}",
        "version": 66,
        "weekStart": "",
        "panels": []  # Aquí se añadirán los paneles dinámicamente
    }

    panel_id = 1
    for sensor_type, panels in dashboard_panels_map.items():
        if sensor_type == "IMU":
            # Para IMU se agrupan las métricas como antes, pero se agrega el prefijo "data."
            for panel_title, fields in panels.items():
                field_filter = " or ".join([f'r["_field"] == "data_{f}"' for f in fields])
                query = f'''
                    from(bucket: "{INFLUXDB_BUCKET}")
                    |> range(start: v.timeRangeStart, stop: v.timeRangeStop)
                    |> filter(fn: (r) => r["topic"] == "Si/{uuid}/{sensor_type}")
                    |> filter(fn: (r) => {field_filter})
                    |> aggregateWindow(every: v.windowPeriod, fn: mean, createEmpty: true)
                    |> yield(name: "mean")
                    '''
                panel = {
                    "id": panel_id,
                    "title": f"{panel_title} ({sensor_type}) - UUID: {uuid}",
                    "type": "timeseries",
                    "datasource": "InfluxDB",
                    "gridPos": {
                        "x": 0,
                        "y": (panel_id - 1) * 10,
                        "w": 24,
                        "h": 9
                    },
                    "fieldConfig": {
                        "defaults": {
                            "custom": {
                                "drawStyle": "line",
                                "lineWidth": 1,
                                "fillOpacity": 20,
                                "pointSize": 5,
                                "showPoints": "auto",
                                "spanNulls": True
                            },
                            "color": {
                                "mode": "palette-classic"
                            }
                        },
                        "overrides": []
                    },
                    "options": {
                        "tooltip": {
                            "mode": "single",
                            "sort": "none"
                        },
                        "legend": {
                            "showLegend": True,
                            "displayMode": "list",
                            "placement": "bottom"
                        }
                    },
                    "targets": [
                        {
                            "query": query
                        }
                    ]
                }
                dashboard["panels"].append(panel)
                panel_id += 1
        elif sensor_type in ("GPS", "ENV"):
            # Para GPS y ENV se crea un panel por cada métrica
            for panel_title, fields in panels.items():
                for f in fields:
                    data_field = f"data_{f}"
                    query = f'''
                    from(bucket: "{INFLUXDB_BUCKET}")
                    |> range(start: v.timeRangeStart, stop: v.timeRangeStop)
                    |> filter(fn: (r) => r["topic"] == "Si/{uuid}/{sensor_type}")
                    |> filter(fn: (r) => r["_field"] == "{data_field}")
                    |> aggregateWindow(every: v.windowPeriod, fn: mean, createEmpty: true)
                    |> yield(name: "mean")
                    '''
                    panel = {
                        "id": panel_id,
                        "title": f"{f} ({sensor_type}) - UUID: {uuid}",
                        "type": "timeseries",
                        "datasource": "InfluxDB",
                        "gridPos": {
                            "x": 0,
                            "y": (panel_id - 1) * 10,
                            "w": 24,
                            "h": 9
                        },
                        "fieldConfig": {
                            "defaults": {
                                "custom": {
                                    "drawStyle": "line",
                                    "lineWidth": 1,
                                    "fillOpacity": 20,
                                    "pointSize": 5,
                                    "showPoints": "auto",
                                    "spanNulls": True
                                },
                                "color": {
                                    "mode": "palette-classic"
                                }
                            },
                            "overrides": []
                        },
                        "options": {
                            "tooltip": {
                                "mode": "single",
                                "sort": "none"
                            },
                            "legend": {
                                "showLegend": True,
                                "displayMode": "list",
                                "placement": "bottom"
                            }
                        },
                        "targets": [
                            {
                                "query": query
                            }
                        ]
                    }
                    dashboard["panels"].append(panel)
                    panel_id += 1

    # Se guarda el dashboard en un archivo JSON
    file_path = os.path.join(DASHBOARD_PATH, f"{uuid}.json")
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    with open(file_path, 'w') as f:
        json.dump(dashboard, f, indent=4)

    print(f"Dashboard creado: {file_path}")

def main():
    print("Iniciando detección de UUIDs...")
    existing_uuids = set()

    while True:
        uuids = set(get_uuids())
        new_uuids = uuids - existing_uuids

        for uuid_val in new_uuids:
            create_dashboard(uuid_val)
            existing_uuids.add(uuid_val)

        time.sleep(10)

if __name__ == "__main__":
    main()