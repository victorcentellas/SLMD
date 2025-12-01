FROM python:3.11-slim

WORKDIR /app

COPY detect_uuids.py .

RUN pip install influxdb-client

CMD ["python", "detect_uuids.py"]
