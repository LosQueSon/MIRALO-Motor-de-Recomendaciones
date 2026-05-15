#!/bin/bash
set -e

echo "Starting MIRALO FastAPI application..."

# Cambiar al directorio de la app
cd /home/site/wwwroot

# Instalar dependencias (por si acaso)
pip install --no-cache-dir -r requirements.txt

# Arrancar con gunicorn + uvicorn worker
gunicorn --workers 2 --worker-class uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000 --timeout 60 main:app

