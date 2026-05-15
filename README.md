# MIRALO Recommendation Engine

Servicio de recomendaciones en **FastAPI** usando el dataset de películas y los modelos entrenados en Python.

## Endpoints

### Recomendaciones
- `POST /recommendations/user` - Recomendaciones personales
- `POST /recommendations/room` - Recomendaciones para grupo
- `GET /genres` - Listado de géneros disponibles
- `GET /movies` - Catálogo de películas
- `GET /movies/{movie_id}` - Detalles de película

### Votación Grupal (Poll)
- `POST /recommendations/room/poll` - Crear poll de votación
- `GET /recommendations/room/poll/{poll_id}` - Consultar estado del poll
- `POST /recommendations/room/poll/{poll_id}/vote` - Votar en poll

### Sistema
- `GET /health` - Health check
- `GET /model/report` - Reporte del modelo entrenado

### Aliases compatibles
- `GET /ml/health`, `GET /ml/report`
- `POST /ml/predict`, `POST /ml/predict-room`
- `POST /ml/predict-room/poll`

## Requisitos

- Python 3.10+
- Dependencias en `requirements.txt`
- Modelos en `ml_models/`
- Dataset en `data/`

## Desarrollo Local

```powershell
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 3000 --reload
```

## Despliegue en Azure

### GitHub Actions (Automático)

1. Crear App Service:
```bash
az group create --name miralo-rg --location canadacentral
az appservice plan create --name miralo-plan --resource-group miralo-rg --sku B1 --is-linux
az webapp create --resource-group miralo-rg --plan miralo-plan --name miralo-ai --runtime "PYTHON|3.11"
```

2. Agregar `AZURE_PUBLISH_PROFILE` en GitHub Secrets

3. Push a `AI-engine-for-recommendations-and-voting` y GitHub Actions deploya automáticamente

### Manual con Azure CLI

```powershell
az login
az group create --name miralo-rg --location canadacentral
az appservice plan create --name miralo-plan --resource-group miralo-rg --sku B1 --is-linux
az webapp create --resource-group miralo-rg --plan miralo-plan --name miralo-ai --runtime "PYTHON|3.11"
az webapp config set --resource-group miralo-rg --name miralo-ai --startup-file "bash startup.sh"
zip -r release.zip . --exclude "*.git*" "__pycache__/*" "*.pyc"
az webapp deployment source config-zip --resource-group miralo-rg --name miralo-ai --src release.zip
az webapp log tail --resource-group miralo-rg --name miralo-ai
```

## Notas

- Backend puro Python + FastAPI
- Votación grupal en memoria
- Modelos ML se cargan al iniciar
