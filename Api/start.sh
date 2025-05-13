#!/bin/bash
pip install --no-cache-dir -r dependencias.txt
uvicorn api:app --host 0.0.0.0 --port 8000 --reload # Lanza la API FastAPI
