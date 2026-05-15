# MIRALO Recommendation Engine
Servicio de recomendaciones en **FastAPI** usando el dataset de películas y los modelos entrenados en Python.
## Endpoints
- `GET /health`
- `GET /model/report`
- `GET /genres`
- `GET /movies`
- `GET /movies/{movie_id}`
- `POST /recommendations/user`
- `POST /recommendations/room`
También están disponibles los aliases compatibles:
- `GET /ml/health`
- `GET /ml/report`
- `POST /ml/predict`
- `POST /ml/predict-room`
## Requisitos
- Python 3.10+
- Dependencias en `requirements.txt`
- Modelos en `ml_models/`
- Dataset en `data/`
## Ejecutar localmente
```powershell
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 3000 --reload
```
## Entrenar el modelo
```powershell
python ml\training\ml_model_training.py
```
## Notas
- El proyecto ya no usa Node.js ni TypeScript.
- El backend ahora corre solo con Python + FastAPI.
