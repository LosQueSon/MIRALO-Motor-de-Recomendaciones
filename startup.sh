#!/bin/bash
set -e
cd /home/site/wwwroot
pip install --quiet -r requirements.txt
exec python -m gunicorn \
  --workers 1 \
  --worker-class uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8000 \
  --timeout 120 \
  main:app
