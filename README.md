# MIRALO — Motor de Recomendaciones

API REST para recomendaciones de películas y series en grupo, con sistema de votación por sala. Construida con **FastAPI** y desplegada en **Azure App Service (Linux, Basic B1)**.

---

## Endpoints principales

| Método | Ruta | Descripción |
|--------|------|-------------|
| `GET`  | `/health` | Estado del servicio |
| `POST` | `/recommendations/room` | Recomendaciones para una sala de usuarios |
| `POST` | `/recommendations/room/poll` | Crea encuesta con las 3 mejores opciones |
| `GET`  | `/recommendations/room/poll/{pollId}` | Estado de la encuesta y ganador |
| `POST` | `/recommendations/room/poll/{pollId}/vote` | Registra un voto |

Documentación interactiva disponible en `/docs`.

---

## Uso rápido

### Recomendaciones para una sala

```http
POST /recommendations/room
Content-Type: application/json

[
  {"userId": "user1", "favoriteGenre": "Drama"},
  {"userId": "user2", "favoriteGenre": "Action"},
  {"userId": "user3", "favoriteGenre": "Action"}
]
```

### Crear encuesta y votar

```http
POST /recommendations/room/poll
# mismo body — devuelve pollId + 3 opciones

POST /recommendations/room/poll/{pollId}/vote
{"userId": "user1", "movieId": 34}

GET /recommendations/room/poll/{pollId}
# devuelve votos actuales y winner
```

---

## Ejecutar localmente

```bash
pip install -r requirements.txt
uvicorn main:app --reload --port 3000
```

---

## Arquitectura y decisiones técnicas

### Fase 1 — Modelo XGBoost (experimental)

El proyecto arrancó entrenando un modelo de **XGBoost** sobre el dataset MovieLens (9 742 películas, 100 836 ratings) para predecir si un usuario va a "gustar" una película basándose en sus géneros.

**Pipeline de entrenamiento** (`ml/training/ml_model_training.py`):
- Target binario: `rating >= 3.5` → "Like"
- Features: 20 géneros one-hot encoded via `MultiLabelBinarizer`
- Dos modelos comparados: XGBoost (531 KB) y Random Forest (11 MB)

**Métricas obtenidas:**

| Modelo | Accuracy | Precision | Recall | F1 | AUC-ROC |
|--------|----------|-----------|--------|----|---------|
| XGBoost | 63.3% | 65.3% | 85.2% | 74.0% | 63.7% |
| Random Forest | 63.4% | 65.5% | 84.8% | 73.9% | 63.9% |

XGBoost fue elegido por ser 20× más pequeño con prácticamente la misma precisión.

---

### Por qué XGBoost no se desplegó en Azure Basic (B1)

Durante el proceso de despliegue encontramos varias limitantes críticas que hacían inviable el uso del modelo en producción con el plan Basic.

#### 1. Tiempo de arranque superior al timeout de Azure (230 s)

Azure App Service Linux envía un HTTP GET `/` al container cuando arranca. Si no recibe respuesta en **230 segundos**, mata el container con `ContainerTimeout`. El startup del modelo bloqueaba el worker completo:

```
joblib.load(xgb_model)              ~10 s
pd.read_csv(movies.csv)              ~3 s
mlb.transform(9 742 movies)         ~45 s   ← cuello de botella en B1
model.predict_proba(X_all 9742×20)  ~15 s
np.argsort(probs)                    ~1 s
                                   -------
                                   ~74 s promedio — picos > 230 s bajo carga
```

El plan B1 usa CPU compartida y con burst de otras aplicaciones en el mismo host, el startup superaba el límite de forma intermitente.

#### 2. Consumo de memoria con múltiples workers

| Componente | RAM por worker |
|---|---|
| Python runtime + FastAPI | ~80 MB |
| `movies_df` (9 742 filas en pandas) | ~15 MB |
| Modelo XGBoost cargado con joblib | ~8 MB |
| Matriz pre-computada `probs_all` | ~5 MB |
| **Total por worker** | **~108 MB** |

Con 2 workers Gunicorn (configuración original) el proceso sumaba ~350 MB solo de applicación, más el overhead del SO. Aunque el B1 tiene 1.75 GB de RAM, el problema era el pico de memoria **durante** la carga simultánea de ambos workers al arrancar.

#### 3. `pip install` en cada cold start sin caché

El `startup.sh` original ejecutaba `pip install --no-cache-dir -r requirements.txt` en cada arranque. Con el stack ML completo esto añadía **3–5 minutos** antes de que gunicorn siquiera iniciara, haciendo el timeout de 230 s imposible de cumplir.

Los intentos de solución fallaron en cascada:
- Bundlear paquetes en el ZIP (`--target .python_packages/`) → `webapps-deploy@v3` usa la API Kudu directa que no inyecta automáticamente `PYTHONPATH` con startup commands personalizados
- Carga del modelo en background thread → el worker tardaba en responder al primer HTTP probe
- `SCM_DO_BUILD_DURING_DEPLOYMENT=true` → solo aplica a deploys por Git/SCM, no a ZIP deploy vía GitHub Actions

#### 4. El modelo no aportaba personalización real por usuario

Al auditar el código de inferencia, se descubrió que el modelo XGBoost recibía únicamente los géneros de **la película** como features — los del usuario solo se usaban para filtrar el resultado, no para generar la predicción:

```python
# Cada request hacía 9 742 llamadas individuales al modelo
for _, row in movies_df.iterrows():
    movie_encoded = mlb.transform([row['genres'].split('|')])
    prob = model.predict_proba(movie_encoded)[0][1]  # score fijo por género de película
```

El score era idéntico para cualquier usuario que pidiera el mismo género. El modelo aprendió "qué géneros tienden a gustar en general", no preferencias individuales. Esto equivale funcionalmente a un sistema de pesos por género — implementable sin ML.

---

### Solución adoptada — Recomendador por géneros

Dado que el modelo XGBoost no aportaba personalización adicional, se reemplazó por un **algoritmo de scoring basado en frecuencia de géneros** sin dependencias externas:

```python
# Pesos: cuántos usuarios en la sala pidieron cada género
genre_weights = Counter(genre for user in users for genre in user.favoriteGenres)

# Score de cada película = géneros coincidentes ponderados / total peticiones
score = sum(genre_weights[g] for g in movie.genres) / sum(genre_weights.values())
```

**Impacto:**

| Métrica | Con XGBoost | Con género-scoring |
|---|---|---|
| Cold start | > 230 s (timeout) | ~20 s |
| RAM steady-state | ~350 MB (2 workers) | ~80 MB |
| Paquetes de producción | 9 (200 MB instalados) | 4 (< 10 MB) |
| Personalización real | No | No (equivalente) |
| Disponibilidad en B1 | ✗ Falla | ✓ Funciona |

El catálogo cubre 60 títulos populares de películas y series en 15 géneros. La interfaz de API se mantuvo idéntica — sin cambios en el frontend.

---

## Dataset de referencia

Los datos de entrenamiento se conservan en `data/` como registro del experimento con XGBoost. **No se usan en producción.**

| Archivo | Filas | Descripción |
|---------|-------|-------------|
| `data/movies.csv` | 9 742 | Catálogo MovieLens con títulos y géneros |
| `data/ratings.csv` | 100 836 | Ratings de usuarios (escala 0.5–5.0) |

El código de entrenamiento está en `ml/training/ml_model_training.py`.

---

## Stack de producción

```
FastAPI 0.115  ·  Uvicorn  ·  Gunicorn (1 worker)
Azure App Service Linux B1  ·  Python 3.11
```
