#!/bin/bash
set -e

cd /home/site/wwwroot

# Packages are bundled in .python_packages/lib/site-packages inside the deploy
# zip.  Azure automatically adds that path to PYTHONPATH, so "python -m gunicorn"
# finds gunicorn without needing the executable to be on PATH.
# If an Oryx-built /antenv exists (SCM deploy), prefer that instead.
if [ -d "/antenv" ]; then
    source /antenv/bin/activate
fi

# Single worker keeps memory under ~200 MB on the Azure Basic (B1) plan.
# Timeout raised to 120 s for cold-start model loading on B1 CPU.
python -m gunicorn \
  --workers 1 \
  --worker-class uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8000 \
  --timeout 120 \
  main:app
