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
    client = InfluxDBClient(url=INFLUXDB_URL, token=INFLUXDB_TOKEN, org=INFLUXDB_ORG)
    query =  f'''
    from(bucket: "{INFLUXDB_BUCKET}")
      |> range(start: -1h)
      |> filter(fn: (r) => r["topic"] =~ /Si\/[a-z0-9-]+\/10DOF/)
      |> distinct(column: "topic")
    '''
    result = client.query_api().query(query)
    
    uuids = []
    for table in result:
        for record in table.records:
            uuid_valor= record.values.get("topic").split("/")[1]
            uuids.append(uuid_valor)

    return uuids

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
        "panels": [
            {
                "id": 1,
                "title": f"Acelerometro UUID: {str(uuid)}",
                "type": "graph",
                "datasource": "InfluxDB",
                "gridPos": {
                    "x": 0,
                    "y": 0,
                    "w": 24,
                    "h": 9
                },
                "custom":{
                    "drawStyle": "line"
                },
                "targets": [
                    {
                        "query": f'''
                        from(bucket: "{str(INFLUXDB_BUCKET)}")
                        |> range(start: v.timeRangeStart, stop: v.timeRangeStop)
                        |> filter(fn: (r) => r["topic"] == "Si/{str(uuid)}/10DOF")
                        |> filter(fn: (r) => r["_field"] == "data_acelerometro_x" or r["_field"] == "data_acelerometro_y" or r["_field"] == "data_acelerometro_z")
                        |> aggregateWindow(every: v.windowPeriod, fn: mean, createEmpty: false)
                        |> yield(name: "mean")
                        
                        '''
                    }
                ]
            }
        ],
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
        "weekStart": ""
    }

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
        
        time.sleep(10)

if __name__ == "__main__":
    main()
