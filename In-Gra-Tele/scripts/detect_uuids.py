#!/usr/bin/env python3

import uuid
import os
import json
import time
import re
from influxdb_client import InfluxDBClient

INFLUXDB_URL = "http://172.21.0.3:8086"
INFLUXDB_TOKEN = "hQuGGvtteZvXhCdiTE_CcG1MCIOFe_D4o8HJUWonWKhOx2jyUqUsckGTJKeboN0hK83M1MWpjS-fvgyAWDw1hA=="
INFLUXDB_ORG = "UCLM"
INFLUXDB_BUCKET = "datos"
DASHBOARD_PATH = "../grafana/dashboards"

def get_uuids():
    try:
        client = InfluxDBClient(url=INFLUXDB_URL, token=INFLUXDB_TOKEN, org=INFLUXDB_ORG)
        query = f'''
        from(bucket: "{INFLUXDB_BUCKET}")
          |> range(start: -1h)
          |> filter(fn: (r) => r["topic"] =~ /Si\/[a-z0-9-]+\/10DOF/)
          |> distinct(column: "topic")
        '''
        result = client.query_api().query(query)
        
        uuids = []
        for table in result:
            for record in table.records:
                uuid_valor = record.values.get("topic").split("/")[1]
                uuids.append(uuid_valor)

        return uuids
    except Exception as e:
        print(f"❌ Error general: {e}")
        return []

def create_dashboard(uuid):
    # Limpia el valor existente de uuid (sin llamar a uuid.uuid4())
    uuid_clean = re.sub(r'[^a-zA-Z0-9-]', '', str(uuid))
    uuid_clean = uuid_clean[:8]
        
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
        "title": f"Dashboard {str(uuid)}",
        "version": 66,
        "weekStart": "",
        "panels": []  # ✅ Inicializa una lista vacía para añadir paneles después
    }
    panel_id = 1

    
    metricas = ["acelerometro", "giroscopio", "magnetometro"]
    
    for metrica in metricas:
        panel = {
            "id": panel_id,
            "title": f"{metrica.capitalize()} UUID: {str(uuid)}",
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
                    "query": f'''
                    from(bucket: "{INFLUXDB_BUCKET}")
                    |> range(start: v.timeRangeStart, stop: v.timeRangeStop)
                    |> filter(fn: (r) => r["topic"] == "Si/{str(uuid)}/10DOF")
                    |> filter(fn: (r) => r["_field"] == "data_{str(metrica)}_x" or r["_field"] == "data_{str(metrica)}_y" or r["_field"] == "data_{str(metrica)}_z")
                    |> aggregateWindow(every: v.windowPeriod, fn: mean, createEmpty: true)
                    |> yield(name: "mean")
                    '''
                }
            ]
        }
        
        dashboard["panels"].append(panel)
        panel_id += 1
    

    # ✅ Panel para la presión (se añade después de los otros paneles)
    panel_presion = {
        "id": panel_id,
        "title": f"Presion UUID: {str(uuid)}",
        "type": "timeseries",
        "datasource": "InfluxDB",
        "gridPos": {
            "x": 0,
            "y": (panel_id - 1) * 10,  # Posiciona el panel después de los otros
            "w": 24,
            "h": 9
        },
        "fieldConfig": {
            "defaults": {
                "custom": {
                    "drawStyle": "line",
                    "lineWidth": 2,
                    "fillOpacity": 30,
                    "pointSize": 4,
                    "showPoints": "always"
                },
                "color": {
                    "mode": "continuous-GrYlRd"
                }
            }
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
                "query": f'''
                from(bucket: "{INFLUXDB_BUCKET}")
                |> range(start: v.timeRangeStart, stop: v.timeRangeStop)
                |> filter(fn: (r) => r["topic"] == "Si/{str(uuid)}/10DOF")
                |> filter(fn: (r) => r["_field"] == "data_presion")
                |> aggregateWindow(every: v.windowPeriod, fn: mean, createEmpty: true)
                |> yield(name: "mean")
                '''
            }
        ]
    }
    
    dashboard["panels"].append(panel_presion)

    # ✅ Usa uuid_clean para crear el archivo
    file_path = os.path.join(DASHBOARD_PATH, f"{uuid}.json")
    os.makedirs(os.path.dirname(file_path), exist_ok=True)

    # ✅ Guarda el JSON correctamente
    with open(file_path, 'w') as f:
        json.dump(dashboard, f, indent=4)

    print(f"✅ Dashboard creado: {file_path}")

def main():
    existing_uuids = set()

    while True:
        uuids = set(get_uuids())
        new_uuids = uuids - existing_uuids

        for uuid in new_uuids:
            create_dashboard(uuid)
            existing_uuids.add(uuid)

        # 🔁 Pausa de 10 segundos antes de consultar nuevamente
        time.sleep(10)

if __name__ == "__main__":
    main()
