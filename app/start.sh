#!/bin/bash

# Lanzar la API FastAPI
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
