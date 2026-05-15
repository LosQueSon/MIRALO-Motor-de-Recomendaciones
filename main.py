from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
from typing import Any, List, Optional
from uuid import uuid4

from fastapi import Body, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# Catalogue — movies and series with genre tags
# ---------------------------------------------------------------------------
CATALOGUE: list[dict[str, Any]] = [
    {"movieId": 1,  "title": "The Dark Knight",                          "genres": ["Action", "Crime", "Drama"],                    "type": "movie"},
    {"movieId": 2,  "title": "Die Hard",                                 "genres": ["Action", "Thriller"],                          "type": "movie"},
    {"movieId": 3,  "title": "Mad Max: Fury Road",                       "genres": ["Action", "Adventure", "Sci-Fi"],               "type": "movie"},
    {"movieId": 4,  "title": "John Wick",                                "genres": ["Action", "Thriller", "Crime"],                 "type": "movie"},
    {"movieId": 5,  "title": "Avengers: Endgame",                        "genres": ["Action", "Adventure", "Sci-Fi"],               "type": "movie"},
    {"movieId": 6,  "title": "Top Gun: Maverick",                        "genres": ["Action", "Drama"],                             "type": "movie"},
    {"movieId": 7,  "title": "Mission: Impossible – Fallout",            "genres": ["Action", "Adventure", "Thriller"],             "type": "movie"},
    {"movieId": 8,  "title": "Indiana Jones and the Raiders of the Lost Ark", "genres": ["Action", "Adventure"],                   "type": "movie"},
    {"movieId": 9,  "title": "The Matrix",                               "genres": ["Action", "Sci-Fi"],                            "type": "movie"},
    {"movieId": 10, "title": "Everything Everywhere All at Once",        "genres": ["Action", "Adventure", "Comedy", "Sci-Fi"],     "type": "movie"},
    {"movieId": 11, "title": "The Shawshank Redemption",                 "genres": ["Drama"],                                       "type": "movie"},
    {"movieId": 12, "title": "Forrest Gump",                             "genres": ["Drama", "Romance"],                            "type": "movie"},
    {"movieId": 13, "title": "Parasite",                                 "genres": ["Drama", "Thriller"],                           "type": "movie"},
    {"movieId": 14, "title": "Oppenheimer",                              "genres": ["Drama", "Thriller"],                           "type": "movie"},
    {"movieId": 15, "title": "La La Land",                               "genres": ["Drama", "Romance", "Musical"],                 "type": "movie"},
    {"movieId": 16, "title": "Gone Girl",                                "genres": ["Drama", "Mystery", "Thriller"],                "type": "movie"},
    {"movieId": 17, "title": "The Godfather",                            "genres": ["Crime", "Drama"],                              "type": "movie"},
    {"movieId": 18, "title": "Interstellar",                             "genres": ["Adventure", "Drama", "Sci-Fi"],                "type": "movie"},
    {"movieId": 19, "title": "Blade Runner 2049",                        "genres": ["Drama", "Mystery", "Sci-Fi"],                  "type": "movie"},
    {"movieId": 20, "title": "Dune",                                     "genres": ["Adventure", "Drama", "Sci-Fi"],                "type": "movie"},
    {"movieId": 21, "title": "Jurassic Park",                            "genres": ["Adventure", "Sci-Fi", "Thriller"],             "type": "movie"},
    {"movieId": 22, "title": "The Lord of the Rings: The Fellowship",    "genres": ["Action", "Adventure", "Drama", "Fantasy"],     "type": "movie"},
    {"movieId": 23, "title": "Avatar",                                   "genres": ["Action", "Adventure", "Fantasy", "Sci-Fi"],    "type": "movie"},
    {"movieId": 24, "title": "Get Out",                                  "genres": ["Horror", "Mystery", "Thriller"],               "type": "movie"},
    {"movieId": 25, "title": "It",                                       "genres": ["Horror", "Drama"],                             "type": "movie"},
    {"movieId": 26, "title": "Spirited Away",                            "genres": ["Adventure", "Animation", "Fantasy"],           "type": "movie"},
    {"movieId": 27, "title": "Spider-Man: Into the Spider-Verse",        "genres": ["Action", "Adventure", "Animation"],            "type": "movie"},
    {"movieId": 28, "title": "The Grand Budapest Hotel",                 "genres": ["Comedy", "Drama"],                             "type": "movie"},
    {"movieId": 29, "title": "Superbad",                                 "genres": ["Comedy"],                                      "type": "movie"},
    {"movieId": 30, "title": "Barbie",                                   "genres": ["Adventure", "Comedy", "Fantasy"],              "type": "movie"},
    {"movieId": 31, "title": "Breaking Bad",                             "genres": ["Crime", "Drama", "Thriller"],                  "type": "series"},
    {"movieId": 32, "title": "Stranger Things",                          "genres": ["Drama", "Fantasy", "Horror", "Mystery", "Sci-Fi"], "type": "series"},
    {"movieId": 33, "title": "Game of Thrones",                          "genres": ["Action", "Adventure", "Drama", "Fantasy"],     "type": "series"},
    {"movieId": 34, "title": "The Last of Us",                           "genres": ["Action", "Adventure", "Drama", "Horror"],      "type": "series"},
    {"movieId": 35, "title": "Squid Game",                               "genres": ["Action", "Drama", "Mystery", "Thriller"],      "type": "series"},
    {"movieId": 36, "title": "Money Heist",                              "genres": ["Action", "Crime", "Mystery", "Thriller"],      "type": "series"},
    {"movieId": 37, "title": "Narcos",                                   "genres": ["Crime", "Drama", "Thriller"],                  "type": "series"},
    {"movieId": 38, "title": "True Detective",                           "genres": ["Crime", "Drama", "Mystery", "Thriller"],       "type": "series"},
    {"movieId": 39, "title": "Mindhunter",                               "genres": ["Crime", "Drama", "Thriller"],                  "type": "series"},
    {"movieId": 40, "title": "Ozark",                                    "genres": ["Crime", "Drama", "Thriller"],                  "type": "series"},
    {"movieId": 41, "title": "Better Call Saul",                         "genres": ["Crime", "Drama"],                              "type": "series"},
    {"movieId": 42, "title": "Peaky Blinders",                           "genres": ["Crime", "Drama"],                              "type": "series"},
    {"movieId": 43, "title": "Black Mirror",                             "genres": ["Drama", "Sci-Fi", "Thriller"],                 "type": "series"},
    {"movieId": 44, "title": "Dark",                                     "genres": ["Crime", "Drama", "Mystery", "Sci-Fi"],         "type": "series"},
    {"movieId": 45, "title": "Severance",                                "genres": ["Drama", "Mystery", "Sci-Fi", "Thriller"],      "type": "series"},
    {"movieId": 46, "title": "The Boys",                                 "genres": ["Action", "Comedy", "Crime", "Sci-Fi"],         "type": "series"},
    {"movieId": 47, "title": "The Mandalorian",                          "genres": ["Action", "Adventure", "Fantasy", "Sci-Fi"],    "type": "series"},
    {"movieId": 48, "title": "House of the Dragon",                      "genres": ["Action", "Adventure", "Drama", "Fantasy"],     "type": "series"},
    {"movieId": 49, "title": "The Witcher",                              "genres": ["Action", "Adventure", "Fantasy"],              "type": "series"},
    {"movieId": 50, "title": "Arcane",                                   "genres": ["Action", "Adventure", "Animation", "Fantasy"], "type": "series"},
    {"movieId": 51, "title": "Wednesday",                                "genres": ["Comedy", "Fantasy", "Horror", "Mystery"],      "type": "series"},
    {"movieId": 52, "title": "The Haunting of Hill House",               "genres": ["Drama", "Horror", "Mystery"],                  "type": "series"},
    {"movieId": 53, "title": "Succession",                               "genres": ["Drama"],                                       "type": "series"},
    {"movieId": 54, "title": "The Crown",                                "genres": ["Drama"],                                       "type": "series"},
    {"movieId": 55, "title": "The Bear",                                 "genres": ["Comedy", "Drama"],                             "type": "series"},
    {"movieId": 56, "title": "Ted Lasso",                                "genres": ["Comedy", "Drama"],                             "type": "series"},
    {"movieId": 57, "title": "The Office",                               "genres": ["Comedy"],                                      "type": "series"},
    {"movieId": 58, "title": "Friends",                                  "genres": ["Comedy", "Romance"],                           "type": "series"},
    {"movieId": 59, "title": "Normal People",                            "genres": ["Drama", "Romance"],                            "type": "series"},
    {"movieId": 60, "title": "Sherlock",                                 "genres": ["Crime", "Drama", "Mystery"],                   "type": "series"},
]

POLL_TTL_SECONDS = 7200


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------
class RoomUser(BaseModel):
    userId: str
    favoriteGenres: List[str] = Field(default_factory=list)
    favoriteGenre: Optional[str] = None


class RoomRecommendationRequest(BaseModel):
    users: List[RoomUser]
    topK: int = Field(default=10, ge=1, le=50)


class UserRecommendationRequest(BaseModel):
    favoriteGenres: List[str] = Field(default_factory=list)
    favoriteGenre: Optional[str] = None
    topK: int = Field(default=10, ge=1, le=50)
    threshold: float = Field(default=0.5, ge=0.0, le=1.0)


class RoomPollVoteRequest(BaseModel):
    userId: str
    movieId: int


# ---------------------------------------------------------------------------
# Recommendation logic
# ---------------------------------------------------------------------------
def _genres_for(user: RoomUser) -> list[str]:
    genres = list(user.favoriteGenres)
    if user.favoriteGenre and user.favoriteGenre not in genres:
        genres.append(user.favoriteGenre)
    return genres


def _score_movie(movie_genres: list[str], genre_weights: Counter) -> float:
    total = sum(genre_weights.values())
    if total == 0:
        return 0.0
    return sum(genre_weights.get(g, 0) for g in movie_genres) / total


def recommend(genre_weights: Counter, top_k: int = 10) -> list[dict[str, Any]]:
    if not genre_weights:
        return []
    scored = []
    for item in CATALOGUE:
        score = _score_movie(item["genres"], genre_weights)
        if score > 0:
            matching = [g for g in item["genres"] if genre_weights.get(g, 0) > 0]
            scored.append({
                "movieId": item["movieId"],
                "title": item["title"],
                "genres": item["genres"],
                "type": item["type"],
                "consensus_score": round(score, 4),
                "reasons": [f"Coincide con los géneros: {', '.join(matching)}"],
            })
    scored.sort(key=lambda x: (-x["consensus_score"], x["title"]))
    return scored[:top_k]


def room_genre_weights(users: list[RoomUser]) -> Counter:
    weights: Counter = Counter()
    for user in users:
        for genre in _genres_for(user):
            if genre:
                weights[genre] += 1
    return weights


# ---------------------------------------------------------------------------
# Poll helpers
# ---------------------------------------------------------------------------
_polls: dict[str, dict[str, Any]] = {}


def _cleanup_polls() -> None:
    now = datetime.now(timezone.utc)
    stale = [
        pid for pid, poll in _polls.items()
        if (now - datetime.fromisoformat(poll["createdAt"].rstrip("Z")).replace(tzinfo=timezone.utc)).total_seconds() > POLL_TTL_SECONDS
    ]
    for pid in stale:
        del _polls[pid]


def _vote_counts(poll: dict) -> dict[int, int]:
    counts = {int(opt["movieId"]): 0 for opt in poll["options"]}
    for mid in poll["votes"].values():
        counts[int(mid)] = counts.get(int(mid), 0) + 1
    return counts


def _format_poll(poll: dict) -> dict[str, Any]:
    counts = _vote_counts(poll)
    options = [{**opt, "voteCount": counts.get(int(opt["movieId"]), 0)} for opt in poll["options"]]
    options.sort(key=lambda o: (-o["voteCount"], -o["consensus_score"]))
    winner = options[0] if options else None
    return {
        "pollId": poll["pollId"],
        "createdAt": poll["createdAt"],
        "totalUsers": poll["totalUsers"],
        "votesCast": len(poll["votes"]),
        "options": options,
        "winner": winner,
    }


# ---------------------------------------------------------------------------
# FastAPI app
# ---------------------------------------------------------------------------
app = FastAPI(
    title="MIRALO Recommendation Engine",
    version="3.0.0",
    description="Movie and series recommendations for rooms with voting.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def root():
    return {"message": "MIRALO Recommendation Engine API", "docs": "/docs"}


@app.get("/health")
def health():
    return {"status": "ready", "message": "Service ready", "catalogueSize": len(CATALOGUE)}


# ---------------------------------------------------------------------------
# User recommendations
# ---------------------------------------------------------------------------
@app.post("/recommendations/user")
def recommendations_user(payload: UserRecommendationRequest):
    genres = list(payload.favoriteGenres)
    if payload.favoriteGenre and payload.favoriteGenre not in genres:
        genres.append(payload.favoriteGenre)
    weights: Counter = Counter(genres)
    recs = recommend(weights, top_k=payload.topK)
    return {"success": True, "count": len(recs), "recommendations": recs}


# ---------------------------------------------------------------------------
# Room recommendations
# ---------------------------------------------------------------------------
def _room_from_payload(payload: Any) -> tuple[list[RoomUser], int]:
    """Parse room payload in any of the three accepted shapes."""
    if isinstance(payload, list):
        users = [RoomUser(**u) if isinstance(u, dict) else u for u in payload]
        return users, 10
    if isinstance(payload, dict):
        raw_users = payload.get("users", [])
        users = [RoomUser(**u) if isinstance(u, dict) else u for u in raw_users]
        return users, int(payload.get("topK", 10))
    raise HTTPException(status_code=400, detail="Invalid room payload")


@app.post("/recommendations/room")
def recommendations_room(payload: Any = Body(...)):
    users, top_k = _room_from_payload(payload)
    if not users:
        raise HTTPException(status_code=400, detail="No users provided")
    weights = room_genre_weights(users)
    recs = recommend(weights, top_k=top_k)
    return {
        "success": True,
        "totalUsers": len(users),
        "recommendationCount": len(recs),
        "recommendations": recs,
    }


# ---------------------------------------------------------------------------
# Room polls
# ---------------------------------------------------------------------------
@app.post("/recommendations/room/poll")
def create_room_poll(payload: Any = Body(...)):
    _cleanup_polls()
    users, _ = _room_from_payload(payload)
    if not users:
        raise HTTPException(status_code=400, detail="No users provided")
    weights = room_genre_weights(users)
    top3 = recommend(weights, top_k=3)
    if not top3:
        raise HTTPException(status_code=400, detail="No recommendations found for given genres")

    poll_id = str(uuid4())
    _polls[poll_id] = {
        "pollId": poll_id,
        "createdAt": datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
        "totalUsers": len(users),
        "options": top3,
        "votes": {},
    }
    return _format_poll(_polls[poll_id])


@app.get("/recommendations/room/poll/{poll_id}")
def get_room_poll(poll_id: str):
    poll = _polls.get(poll_id)
    if not poll:
        raise HTTPException(status_code=404, detail="Poll not found")
    return _format_poll(poll)


@app.post("/recommendations/room/poll/{poll_id}/vote")
def vote_room_poll(poll_id: str, payload: RoomPollVoteRequest):
    poll = _polls.get(poll_id)
    if not poll:
        raise HTTPException(status_code=404, detail="Poll not found")
    valid_ids = {int(opt["movieId"]) for opt in poll["options"]}
    if int(payload.movieId) not in valid_ids:
        raise HTTPException(status_code=400, detail="Movie is not part of the poll options")
    poll["votes"][payload.userId] = int(payload.movieId)
    return _format_poll(poll)


# ---------------------------------------------------------------------------
# Legacy /ml aliases (backwards compatibility)
# ---------------------------------------------------------------------------
@app.get("/ml/health")
def ml_health():
    return health()


@app.post("/ml/predict")
def ml_predict(payload: UserRecommendationRequest):
    return recommendations_user(payload)


@app.post("/ml/predict-room")
def ml_predict_room(payload: Any = Body(...)):
    return recommendations_room(payload)


@app.post("/ml/predict-room/poll")
def ml_create_room_poll(payload: Any = Body(...)):
    return create_room_poll(payload)


@app.get("/ml/predict-room/poll/{poll_id}")
def ml_get_room_poll(poll_id: str):
    return get_room_poll(poll_id)


@app.post("/ml/predict-room/poll/{poll_id}/vote")
def ml_vote_room_poll(poll_id: str, payload: RoomPollVoteRequest):
    return vote_room_poll(poll_id, payload)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=3000, reload=False)
