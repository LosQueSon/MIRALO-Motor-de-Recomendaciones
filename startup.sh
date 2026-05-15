#!/bin/bash
set -e

cd /home/site/wwwroot

# Prefer Oryx-built venv (SCM deploys) when present.
if [ -d "/antenv" ]; then
    source /antenv/bin/activate
else
    # Explicitly add bundled packages to PYTHONPATH.  Azure only injects this
    # automatically when using the default startup command; custom scripts must
    # set it manually.
    export PYTHONPATH="/home/site/wwwroot/.python_packages/lib/site-packages${PYTHONPATH:+:$PYTHONPATH}"
fi

# Single worker keeps memory under ~200 MB on the Azure Basic (B1) plan.
python -m gunicorn \
  --workers 1 \
  --worker-class uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8000 \
  --timeout 120 \
  main:app
