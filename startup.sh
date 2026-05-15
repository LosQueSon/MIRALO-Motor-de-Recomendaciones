#!/bin/bash
set -e

cd /home/site/wwwroot

# Activate the virtual environment that Oryx (SCM_DO_BUILD_DURING_DEPLOYMENT=true)
# creates during ZIP deployment.  Without this, the packages installed by Oryx
# are not on PATH and gunicorn/uvicorn won't be found.
if [ -d "/antenv" ]; then
    source /antenv/bin/activate
fi

# Single worker keeps memory under ~200 MB on the Azure Basic (B1) plan.
# Timeout raised to 120 s for cold-start model loading on B1 CPU.
gunicorn \
  --workers 1 \
  --worker-class uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8000 \
  --timeout 120 \
  main:app
