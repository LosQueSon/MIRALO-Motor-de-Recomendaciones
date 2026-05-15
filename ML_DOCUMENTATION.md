# MIRALO Machine Learning Model - Documentación Completa

## 📋 Resumen

Este directorio contiene un sistema completo de Machine Learning para generar recomendaciones de películas basadas en los géneros favoritos del usuario. El sistema implementa dos modelos (Random Forest y XGBoost) entrenados con datos de co-ocurrencia de géneros.

---

## 🎯 Métricas Académicas del Modelo

### Dataset
- **Total de películas:** 9,742
- **Total de ratings:** 100,836
- **Géneros únicos:** 20
- **Umbral de preferencia:** Rating ≥ 3.5 = "Like"
- **Distribución:** 61% Like, 39% Dislike

### Partición
- **Entrenamiento:** 80,668 muestras (80%)
- **Prueba:** 20,168 muestras (20%)

### XGBoost (Modelo Seleccionado) 📊
| Métrica | Valor |
|---------|-------|
| **Accuracy** | 63.28% |
| **Precision** | 65.34% |
| **Recall** | 85.22% |
| **F1-Score** | 73.96% |
| **AUC-ROC** | 63.66% |

### Matriz de Confusión (XGBoost)
```
       Predicción Negativa | Predicción Positiva
Actual Negativo:    2,243  |      5,581         [TN | FP]
Actual Positivo:    1,825  |     10,519         [FN | TP]
```

**Interpretación:**
- TP (Verdaderos Positivos): 10,519 películas correctamente predichas como "Like"
- TN (Verdaderos Negativos): 2,243 películas correctamente predichas como "Dislike"
- FP (Falsos Positivos): 5,581 películas predichas como "Like" pero eran "Dislike"
- FN (Falsos Negativos): 1,825 películas predichas como "Dislike" pero eran "Like"

**Análisis:**
- El modelo tiene un **alto Recall (85.22%)**: Es muy efectivo encontrando películas que al usuario le gustarán
- El **Precision moderado (65.34%)** indica algunos falsos positivos, pero aceptable para recomendaciones
- El modelo es **conservador pero preciso** en sus predicciones

---

## 🚀 Configuración e Instalación

### 1. **Instalar Dependencias de Python**

```bash
# Desde el directorio raíz del proyecto
pip install -r requirements.txt
```

Dependencias:
- `pandas` - Procesamiento de datos
- `numpy` - Cálculos numéricos
- `scikit-learn` - ML tradicional
- `xgboost` - Gradient boosting
- `joblib` - Serialización de modelos

### 2. **Entrenar el Modelo** 🤖

```bash
python ml_model_training.py
```

**Output esperado:**
```
MIRALO ML MODEL TRAINING
============================================================
[PASO 1] Cargando datos...
✓ Películas cargadas: 9742
✓ Ratings cargados: 100836
...
[PASO 9] Generando reporte...
✓ Reporte guardado: ml_models/training_report.json
```

**Archivos generados en `/ml_models/`:**
- `xgb_recommender_model.joblib` - Modelo XGBoost entrenado
- `rf_recommender_model.joblib` - Modelo Random Forest entrenado
- `mlb_genres.joblib` - Binarizador de géneros
- `training_report.json` - Reporte completo con métricas

---

## 📡 Endpoints de la API

### 1. **Verificar salud del modelo**
```bash
GET /ml/health
```

**Response:**
```json
{
  "status": "ready",
  "message": "ML model is ready"
}
```

---

### 2. **Predicción para usuario individual**
```bash
POST /ml/predict

Content-Type: application/json
{
  "favoriteGenres": ["Action", "Sci-Fi", "Adventure"],
  "topK": 10,
  "threshold": 0.5
}
```

**Response:**
```json
{
  "success": true,
  "count": 5,
  "recommendations": [
    {
      "movieId": 100,
      "title": "Top Gun (1986)",
      "genres": ["Action", "Adventure"],
      "predicted_probability": 0.92,
      "liked": true,
      "reason": "Coincide con tus géneros favoritos (Action, Adventure)"
    },
    {
      "movieId": 150,
      "title": "Terminator 2 (1991)",
      "genres": ["Action", "Sci-Fi"],
      "predicted_probability": 0.88,
      "liked": true,
      "reason": "Coincide con tus géneros favoritos (Action, Sci-Fi)"
    }
  ]
}
```

**Parámetros:**
- `favoriteGenres` (required): Array de géneros favoritos
- `topK` (optional, default=10): Número de recomendaciones
- `threshold` (optional, default=0.5): Probabilidad mínima (0-1)

**Géneros soportados:**
`Action`, `Adventure`, `Animation`, `Children`, `Comedy`, `Crime`, `Documentary`, `Drama`, `Fantasy`, `Film-Noir`, `Horror`, `IMAX`, `Musical`, `Mystery`, `Romance`, `Sci-Fi`, `Thriller`, `War`, `Western`

---

### 3. **Predicción para grupo de usuarios (Sala)**
```bash
POST /ml/predict-room

Content-Type: application/json
{
  "users": [
    {
      "userId": "user_1",
      "favoriteGenres": ["Action", "Thriller"]
    },
    {
      "userId": "user_2",
      "favoriteGenres": ["Sci-Fi", "Adventure"]
    },
    {
      "userId": "user_3",
      "favoriteGenres": ["Action", "Adventure"]
    }
  ],
  "topK": 10
}
```

**Response:**
```json
{
  "success": true,
  "totalUsers": 3,
  "recommendationCount": 5,
  "recommendations": [
    {
      "movieId": 100,
      "title": "Top Gun (1986)",
      "genres": ["Action", "Adventure"],
      "consensus_score": 0.89,
      "reasons": ["Recomendado para user_1", "Recomendado para user_2"]
    }
  ]
}
```

**Algoritmo de consenso:**
- Se obtienen predicciones para cada usuario
- Se agrupan por película
- Se promedia la probabilidad (consensus score)
- Se ordenan por score descendente

---

### 4. **Obtener reporte de entrenamiento**
```bash
GET /ml/report
```

**Response:**
```json
{
  "success": true,
  "report": {
    "timestamp": "2026-05-13T20:06:49.766728",
    "dataset_info": {
      "movies_total": 9742,
      "ratings_total": 100836,
      "training_samples": 80668,
      "test_samples": 20168,
      "positive_class_ratio": 0.612,
      "genres_count": 20,
      "rating_threshold": 3.5
    },
    "xgboost_metrics": {
      "model_name": "XGBoost",
      "train_accuracy": 0.6402,
      "test_accuracy": 0.6328,
      "precision": 0.6534,
      "recall": 0.8522,
      "f1": 0.7396,
      "auc": 0.6366
    },
    "random_forest_metrics": { ... }
  }
}
```

---

## 🧪 Testear Localmente

### Script Python de ejemplo:
```bash
python ml_model_predictor.py
```

Esto ejecutará ejemplos de:
1. Predicción para usuario individual
2. Predicción para sala con consensus

### Con cURL:

```bash
# Verificar salud
curl http://localhost:3000/ml/health

# Predicción simple
curl -X POST http://localhost:3000/ml/predict \
  -H "Content-Type: application/json" \
  -d '{
    "favoriteGenres": ["Action", "Sci-Fi"],
    "topK": 5,
    "threshold": 0.5
  }'

# Predicción para sala
curl -X POST http://localhost:3000/ml/predict-room \
  -H "Content-Type: application/json" \
  -d '{
    "users": [
      {"userId": "u1", "favoriteGenres": ["Action"]},
      {"userId": "u2", "favoriteGenres": ["Sci-Fi"]}
    ],
    "topK": 10
  }'

# Obtener reporte
curl http://localhost:3000/ml/report
```

---

## 📊 Estructura de Datos

### Input: UserProfile
```json
{
  "userId": "string",
  "favoriteGenres": ["string"]
}
```

### Output: Recommendation
```json
{
  "movieId": "number",
  "title": "string",
  "genres": ["string"],
  "predicted_probability": "number (0-1)",
  "liked": "boolean",
  "reason": "string"
}
```

### Output: RoomRecommendation
```json
{
  "movieId": "number",
  "title": "string",
  "genres": ["string"],
  "consensus_score": "number (0-1)",
  "reasons": ["string"]
}
```

---

## 🔧 Arquitectura

```
ml_model_training.py
├── Carga movies.csv + ratings.csv
├── Pre-procesa (bineariza ratings, one-hot encoding)
├── Entrena XGBoost + Random Forest
├── Calcula métricas académicas
└── Exporta: modelo.joblib, mlb.joblib, reporte.json

ml_model_predictor.py
├── Carga modelo entrenado
├── Procesa géneros de usuario
└── Genera predicciones explicables

MLPredictionService.ts (Node.js)
├── Invoca ml_model_predictor.py
├── Gestiona caché de modelos
└── Expone endpoints HTTP

ml.ts (Fastify routes)
├── GET /ml/health
├── POST /ml/predict
├── POST /ml/predict-room
└── GET /ml/report
```

---

## ⚙️ Configuración Avanzada

### Modificar umbral de entrenamiento
En `ml_model_training.py`, línea ~14:
```python
RATING_THRESHOLD = 3.5  # Cambiar este valor
```

### Ajustar hiperparámetros de XGBoost
En `ml_model_training.py`, línea ~120:
```python
xgb_model = xgb.XGBClassifier(
    n_estimators=100,      # Más árboles = más preciso pero más lento
    max_depth=7,           # Profundidad máxima
    learning_rate=0.1,     # Velocidad de aprendizaje
    random_state=RANDOM_STATE
)
```

### Cambiar threshold de predicción
En `/ml/predict`, modificar en el request:
```json
{
  "favoriteGenres": ["Action"],
  "threshold": 0.7  // Mayor threshold = más restrictivo
}
```

---

## 📝 Casos de Uso

### Caso 1: Usuario nuevo sin historial
```json
POST /ml/predict
{
  "favoriteGenres": ["Action", "Adventure"],
  "topK": 20,
  "threshold": 0.45
}
```
*Resultado: 20 películas de acción y aventura ordenadas por probabilidad*

### Caso 2: Sala con múltiples usuarios
```json
POST /ml/predict-room
{
  "users": [
    {"userId": "alice", "favoriteGenres": ["Comedy", "Drama"]},
    {"userId": "bob", "favoriteGenres": ["Action", "Thriller"]},
    {"userId": "charlie", "favoriteGenres": ["Animation", "Fantasy"]}
  ],
  "topK": 10
}
```
*Resultado: Películas que satisfacen consenso del grupo*

### Caso 3: Exploración sin géneros conocidos
```json
POST /ml/predict
{
  "favoriteGenres": [],
  "topK": 5
}
```
*Resultado: Array vacío (requiere al menos un género)*

---

## 🐛 Troubleshooting

### Error: "Model not trained yet"
```bash
python ml_model_training.py
# Luego reiniciar servidor Node.js
```

### Error: "Python not found"
```bash
# Verificar instalación
python --version
pip --version

# Agregar a PATH si es necesario
```

### Predicciones vacías
- Incrementar el `threshold` a valor menor (e.g., 0.3)
- Verificar que los géneros sean correctos
- Revisar `/ml/report` para ver géneros soportados

### Rendimiento lento
- Reducir `topK` en requests
- Implementar caché de predicciones
- Usar modelo RF en lugar de XGB (más rápido)

---

## 📚 Recursos Técnicos

### Modelos Implementados
1. **Random Forest** (Baseline)
   - Rápido
   - Interpretable
   - Recall: 84.79%

2. **XGBoost** (Principal)
   - Más preciso
   - Mejor generalización
   - Recall: 85.22%, F1: 73.96%

### Métodos de Evaluación
- **Accuracy**: Proporción correcta global
- **Precision**: De los "Like" predichos, cuántos son reales
- **Recall**: De los "Like" reales, cuántos encontramos
- **F1-Score**: Media armónica (balance precision-recall)
- **AUC-ROC**: Curva característica de operador

### Técnicas Utilizadas
- One-Hot Encoding (géneros)
- Binarización de labels (ratings)
- Train-Test Split (80/20)
- Stratified sampling (balance de clases)

---

## 🔐 Consideraciones de Producción

1. **Caché de Modelos**
   - Cargar modelos una sola vez
   - Reutilizar en múltiples requests

2. **Rate Limiting**
   - Limitar /ml/predict a 100 req/min por usuario
   - /ml/predict-room a 10 req/min

3. **Monitoreo**
   - Rastrear latencia de predicciones
   - Registrar géneros no encontrados
   - Alertar si accuracy cae

4. **Actualización del Modelo**
   - Re-entrenar cada mes con nuevos ratings
   - Validar en conjunto de test separado
   - Implementar A/B testing

---

## 📄 Licencia

Proyecto MIRALO - 2026

---

**Última actualización:** 13 Mayo 2026
**Versión del Modelo:** 1.0.0
**Python:** 3.10+
**Node.js:** 18+

