# 🔗 INTEGRACIÓN CON BACKEND AZURE

## ✅ ENDPOINTS COMPATIBLES CON TU BACKEND

Tu backend Azure envía la estructura:

```json
[
  {"userId": "69bb3d5ee1db9d17817b70cb", "favoriteGenre": "Action"},
  {"userId": "69bde9c6c661ee886a15e702", "favoriteGenre": "Sci-Fi"}
]
```

**Nuestros endpoints ahora aceptan ambas estructuras automáticamente:**

---

## 🚀 ENDPOINT 1: POST /ml/predict-room (MAIN)

Este es el endpoint que va a consumir tu backend Azure.

### Opción A - Estructura directa (RECOMENDADA)
```bash
curl -X POST http://localhost:3000/ml/predict-room \
  -H "Content-Type: application/json" \
  -d '[
    {"userId": "69bb3d5ee1db9d17817b70cb", "favoriteGenre": "Action"},
    {"userId": "69bde9c6c661ee886a15e702", "favoriteGenre": "Sci-Fi"}
  ]'
```

**El endpoint hace:**
1. Detecta que es un array
2. Convierte `"favoriteGenre"` → `["favoriteGenre"]` (array)
3. Genera predicciones
4. Retorna consenso del grupo

### Response
```json
{
  "success": true,
  "totalUsers": 2,
  "recommendationCount": 10,
  "recommendations": [
    {
      "movieId": 100,
      "title": "Top Gun (1986)",
      "genres": ["Action", "Adventure"],
      "consensus_score": 0.88,
      "reasons": [
        "Recomendado basado en géneros"
      ]
    },
    {
      "movieId": 150,
      "title": "Terminator 2 (1991)",
      "genres": ["Action", "Sci-Fi"],
      "consensus_score": 0.85,
      "reasons": [...]
    },
    ...
  ]
}
```

---

## 🎯 PARÁMETRO topK

Puedes especificar cuántas recomendaciones quieres:

```bash
curl -X POST http://localhost:3000/ml/predict-room \
  -H "Content-Type: application/json" \
  -d '{
    "users": [
      {"userId": "69bb3d5ee1db9d17817b70cb", "favoriteGenre": "Action"}
    ],
    "topK": 20
  }'
```

---

## 📊 INTERPRETACIÓN DEL SCORE

**consensus_score:** Probabilidad que da el modelo XGBoost

- `0.9` = 90% de probabilidad que guste
- `0.7` = 70% de probabilidad que guste
- `0.5` = 50% de probabilidad que guste (borderline)

Mientras más alto, mejor recomendación.

---

## 🔄 CÓMO SE CALCULA EL CONSENSO

Cuando hay múltiples usuarios:

```
Usuario 1 (Action):
  - Película A: 0.85

Usuario 2 (Sci-Fi):
  - Película A: 0.80

Consenso = (0.85 + 0.80) / 2 = 0.825
```

Se promedian las probabilidades de cada película.

---

## ✅ CASOS DE USO REALES

### Caso 1: Sala con 2 usuarios
```bash
curl -X POST http://localhost:3000/ml/predict-room \
  -H "Content-Type: application/json" \
  -d '[
    {"userId": "user_123", "favoriteGenre": "Comedy"},
    {"userId": "user_456", "favoriteGenre": "Drama"}
  ]'
```

### Caso 2: Sala con muchos usuarios
```bash
curl -X POST http://localhost:3000/ml/predict-room \
  -H "Content-Type: application/json" \
  -d '[
    {"userId": "user1", "favoriteGenre": "Action"},
    {"userId": "user2", "favoriteGenre": "Action"},
    {"userId": "user3", "favoriteGenre": "Comedy"},
    {"userId": "user4", "favoriteGenre": "Drama"},
    {"userId": "user5", "favoriteGenre": "Adventure"}
  ]'
```

---

## 🐍 DESDE PYTHON/BACKEND

Si quieres consumir el endpoint desde tu backend Azure (Node.js/Python):

### Python
```python
import requests
import json

users = [
    {"userId": "69bb3d5ee1db9d17817b70cb", "favoriteGenre": "Action"},
    {"userId": "69bde9c6c661ee886a15e702", "favoriteGenre": "Sci-Fi"}
]

response = requests.post(
    "http://localhost:3000/ml/predict-room",
    json=users,
    headers={"Content-Type": "application/json"}
)

recommendations = response.json()
print(json.dumps(recommendations, indent=2))
```

### Node.js/Express
```javascript
const axios = require('axios');

const users = [
  { userId: "69bb3d5ee1db9d17817b70cb", favoriteGenre: "Action" },
  { userId: "69bde9c6c661ee886a15e702", favoriteGenre: "Sci-Fi" }
];

axios.post('http://localhost:3000/ml/predict-room', users)
  .then(response => {
    console.log(response.data);
  })
  .catch(error => {
    console.error('Error:', error);
  });
```

---

## 📌 RESUMEN INTEGRACIÓN

| Aspecto | Detalles |
|---------|----------|
| **Endpoint** | `POST /ml/predict-room` |
| **Formato Input** | Array de `{userId, favoriteGenre}` |
| **Conversión** | Automática de `favoriteGenre` → array interno |
| **Formato Output** | JSON con `recommendations` |
| **Score** | 0-1 (probabilidad) |
| **Consenso** | Promedio de todas las predicciones |

---

## 🚀 IMPLEMENTACIÓN RÁPIDA

1. **Desde tu backend Azure**, cuando quieras recomendaciones para una sala:

```javascript
// usuarios viene del endpoint:
// https://miralobackend-hqhudshrfbb3hqfu.brazilsouth-01.azurewebsites.net/rooms/:roomId/users/genres

const usuarios = [ 
  {userId: "69bb3d5ee1db9d17817b70cb", favoriteGenre: "Action"},
  {userId: "69bde9c6c661ee886a15e702", favoriteGenre: "Sci-Fi"}
];

// Llama directamente nuestro endpoint (sin transformación)
const response = await fetch('http://ml-service:3000/ml/predict-room', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify(usuarios)
});

const recommendations = await response.json();
// Usar recommendations en tu frontend
```

---

## ✨ TODO LISTO

Los endpoints están listos para:
- ✅ Recibir array de usuarios con `favoriteGenre` singular
- ✅ Convertir automáticamente al formato interno
- ✅ Generar recomendaciones de consenso
- ✅ Retornar score de cada película

**¡Sin cambios en tu backend!**

