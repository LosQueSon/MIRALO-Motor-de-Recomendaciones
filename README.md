# recommendation-engine

Microservicio de recomendaciones para MIRALO, construido con Node.js + TypeScript + Fastify + MongoDB.

El motor utiliza exclusivamente `favoriteGenres` por usuario para aprender relaciones entre generos y recomendar:

- peliculas
- series
- generos

## Caracteristicas

- Arquitectura por capas: API, Service, Model, Data
- Estrategia principal basada en modelo de similitud por co-ocurrencia de generos
- Estrategia fallback rule-based
- Recomendaciones explicables (`reason`)
- Endpoint de entrenamiento y consulta del modelo
- Metricas internas (`/metrics`)
- Pruebas unitarias e integracion
- Dockerfile y `docker-compose.yml` con MongoDB

## Estructura del proyecto

```text
src/
  api/
    createServer.ts
    routes/
  config/
  data/
    mongo.ts
    repositories/
  metrics/
  model/
    GenreSimilarityModel.ts
    scoring.ts
    recommenders/
  service/
  main.ts
test/
  unit/
  integration/
```

## Modelo de IA: co-ocurrencia de generos

Dado un usuario con generos favoritos, por ejemplo:

`["Accion", "Sci-Fi", "Aventura"]`

Se generan pares no dirigidos:

- (Accion, Sci-Fi)
- (Accion, Aventura)
- (Sci-Fi, Aventura)

Se construye una matriz de frecuencias y se normaliza por fila para obtener similitud probabilistica entre generos.

## Formula de scoring

Para items (`movie` y `series`):

`score = w1 * directMatch + w2 * inferredMatch + w3 * popularity`

Pesos por defecto:

- `w1 = 0.55`
- `w2 = 0.30`
- `w3 = 0.15`

## Modelos de datos (MongoDB)

Colecciones:

- `user_preference_profiles`
  - `{ userId, favoriteGenres }`
- `item_metadata`
  - `{ itemId, type, genres, popularityScore }`
- `genre_relations`
  - `{ genre, relatedGenres: [{ genre, score }] }`
- `recommendation_snapshots`
  - `{ userId, recommendations, createdAt }`

## Endpoints

- `GET /health`
- `GET /recommendations/:userId?limit=10`
- `POST /model/train`
- `GET /model/genres`
- `GET /metrics`

### Ejemplo de recomendacion

```json
{
  "itemId": "m1",
  "score": 0.87,
  "type": "movie",
  "reason": "Recomendado porque te gusta Action y se relaciona con Adventure"
}
```

## Como ejecutar local

1. Instalar dependencias
2. Configurar variables de entorno
3. Ejecutar el servidor

```powershell
npm install
Copy-Item .env.example .env
npm run dev
```

### Ejemplo de `.env` para Mongo Compass / Atlas

```dotenv
PORT=3000
MONGO_URI=mongodb+srv://<user>:<password>@cluster0.xxxxx.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0
MONGO_DB_NAME=Miralo
SEED_USERS_FILE=scripts/data/users.seed.json
```

## Conexion a Mongo y carga de usuarios

1. Verifica que `.env` tenga `MONGO_URI` y `MONGO_DB_NAME` apuntando a tu cluster/instancia.
2. Edita `scripts/data/users.seed.json` con tus usuarios y `favoriteGenres`.
3. Ejecuta el seed de usuarios.
4. Comprueba conexion y datos cargados.

Formato esperado para `scripts/data/users.seed.json`:

```json
[
  {
    "userId": "69bec5d853b18a1b217dc0e3",
    "favoriteGenres": ["Action", "Sci-Fi", "Adventure"]
  },
  {
    "id": "69bde9c6c661ee886a15e702",
    "favoriteGenres": ["Drama", "Romance", "Comedy"]
  }
]
```

El seed acepta `userId`, `id` o `_id` (incluyendo formato de export de Compass con `$oid`) para mapear el `userId` interno.

```powershell
npm run seed:users
npm run check:db
```

Si quieres usar otro archivo JSON para seed:

```powershell
$env:SEED_USERS_FILE="scripts/data/users.seed.json"
npm run seed:users
```

## Como entrenar el modelo

```powershell
Invoke-RestMethod -Method Post -Uri http://localhost:3000/model/train
```

Respuesta esperada (ejemplo):

```json
{
  "status": "trained",
  "trainedUsers": 3,
  "relations": 9
}
```

## Como probar endpoints

```powershell
Invoke-RestMethod -Method Get -Uri http://localhost:3000/health
Invoke-RestMethod -Method Get -Uri http://localhost:3000/recommendations/69bec5d853b18a1b217dc0e3?limit=10
Invoke-RestMethod -Method Get -Uri http://localhost:3000/model/genres
Invoke-RestMethod -Method Get -Uri http://localhost:3000/metrics
```

## Pruebas

```powershell
npm test
npm run test:unit
npm run test:integration
```

Incluye casos para:

- usuario sin generos
- generos desconocidos
- modelo sin entrenar
- alto volumen de requests

## Docker

```powershell
docker compose up --build
```

Servicio:

- API: `http://localhost:3000`
- MongoDB: `mongodb://localhost:27017`
