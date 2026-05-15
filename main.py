from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, List, Optional
from uuid import uuid4

import pandas as pd
from fastapi import Body, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from ml.training.ml_model_predictor import MiraloMLPredictor


ROOT_DIR = Path(__file__).resolve().parent
MOVIES_FILE = ROOT_DIR / "data" / "movies.csv"
REPORT_FILE = ROOT_DIR / "ml_models" / "training_report.json"
KNOWN_GENRES = [
    "Action",
    "Adventure",
    "Animation",
    "Children",
    "Comedy",
    "Crime",
    "Documentary",
    "Drama",
    "Fantasy",
    "Film-Noir",
    "Horror",
    "IMAX",
    "Musical",
    "Mystery",
    "Romance",
    "Sci-Fi",
    "Thriller",
    "War",
    "Western",
]


class UserRecommendationRequest(BaseModel):
    favoriteGenres: List[str] = Field(default_factory=list)
    favoriteGenre: Optional[str] = None
    topK: int = Field(default=10, ge=1, le=100)
    threshold: float = Field(default=0.5, ge=0.0, le=1.0)


class RoomUser(BaseModel):
    userId: str
    favoriteGenres: List[str] = Field(default_factory=list)
    favoriteGenre: Optional[str] = None


class RoomRecommendationRequest(BaseModel):
    users: List[RoomUser]
    topK: int = Field(default=10, ge=1, le=100)


class RoomPollVoteRequest(BaseModel):
    userId: str
    movieId: int


class MovieItem(BaseModel):
    movieId: int
    title: str
    genres: List[str]
    popularity: float | None = None


class RecommendationService:
    def __init__(self) -> None:
        self.predictor: Optional[MiraloMLPredictor] = None
        self.movies_df: pd.DataFrame = pd.DataFrame()
        self.load_error: Optional[str] = None
        self.room_polls: dict[str, dict[str, Any]] = {}
        self.reload()

    def reload(self) -> None:
        try:
            predictor = MiraloMLPredictor()
            predictor.load_movies()
            self.predictor = predictor
            self.movies_df = predictor.movies_df.copy() if predictor.movies_df is not None else pd.DataFrame()
            if not self.movies_df.empty:
                self.movies_df["parsed_genres"] = self.movies_df["genres"].apply(self._parse_genres)
            self.load_error = None
        except Exception as exc:  # pragma: no cover - startup protection
            self.predictor = None
            self.movies_df = pd.DataFrame()
            self.load_error = str(exc)

    def is_ready(self) -> bool:
        return self.predictor is not None and not self.movies_df.empty

    def _ensure_ready(self) -> MiraloMLPredictor:
        if not self.predictor or self.movies_df.empty:
            raise HTTPException(status_code=503, detail=self.load_error or "Model or dataset not available")
        return self.predictor

    def _json_safe(self, value: Any) -> Any:
        if isinstance(value, dict):
            return {str(key): self._json_safe(val) for key, val in value.items()}
        if isinstance(value, list):
            return [self._json_safe(item) for item in value]
        if isinstance(value, tuple):
            return [self._json_safe(item) for item in value]
        if hasattr(value, "item") and callable(value.item):
            try:
                return value.item()
            except Exception:
                return value
        return value

    def _room_request_from_payload(self, payload: Any, default_top_k: int = 10) -> RoomRecommendationRequest:
        if isinstance(payload, RoomRecommendationRequest):
            return payload

        if isinstance(payload, list):
            users = [RoomUser(**item) for item in payload]
            return RoomRecommendationRequest(users=users, topK=default_top_k)

        if isinstance(payload, dict):
            users = [RoomUser(**item) for item in payload.get("users", [])]
            top_k = int(payload.get("topK", default_top_k))
            return RoomRecommendationRequest(users=users, topK=max(default_top_k, top_k))

        raise HTTPException(status_code=400, detail="Invalid room payload")

    def _normalize_options(self, options: list[dict[str, Any]]) -> list[dict[str, Any]]:
        cleaned = []
        for option in options:
            item = dict(option)
            item["movieId"] = int(item["movieId"])
            item["consensus_score"] = float(item.get("consensus_score", 0.0))
            cleaned.append(item)
        cleaned.sort(key=lambda item: (-float(item.get("consensus_score", 0.0)), item.get("title", ""), int(item["movieId"])))
        return cleaned

    def _poll_vote_counts(self, poll: dict[str, Any]) -> dict[int, int]:
        counts: dict[int, int] = {int(option["movieId"]): 0 for option in poll.get("options", [])}
        for movie_id in poll.get("votes", {}).values():
            movie_id_int = int(movie_id)
            counts[movie_id_int] = counts.get(movie_id_int, 0) + 1
        return counts

    def _poll_winner(self, poll: dict[str, Any]) -> Optional[dict[str, Any]]:
        options = poll.get("options", [])
        if not options:
            return None

        vote_counts = self._poll_vote_counts(poll)

        def sort_key(option: dict[str, Any]) -> tuple[int, float, int]:
            movie_id = int(option["movieId"])
            return (
                vote_counts.get(movie_id, 0),
                float(option.get("consensus_score", 0.0)),
                -movie_id,
            )

        winner = max(options, key=sort_key)
        winner_copy = dict(winner)
        winner_copy["voteCount"] = vote_counts.get(int(winner_copy["movieId"]), 0)
        return winner_copy

    def _format_poll(self, poll: dict[str, Any]) -> dict[str, Any]:
        vote_counts = self._poll_vote_counts(poll)
        options = []
        for option in poll.get("options", []):
            option_copy = dict(option)
            option_copy["voteCount"] = vote_counts.get(int(option_copy["movieId"]), 0)
            options.append(option_copy)

        return self._json_safe(
            {
                "pollId": poll["pollId"],
                "createdAt": poll["createdAt"],
                "totalUsers": poll.get("totalUsers", 0),
                "votesCast": len(poll.get("votes", {})),
                "options": self._normalize_options(options),
                "winner": self._poll_winner({**poll, "options": options}),
            }
        )

    def _parse_genres(self, raw_genres: Any) -> list[str]:
        if raw_genres is None or (isinstance(raw_genres, float) and pd.isna(raw_genres)):
            return []

        text = str(raw_genres).strip()
        if not text or text == "(no genres listed)":
            return []

        if "|" in text:
            return [genre.strip() for genre in text.split("|") if genre.strip()]

        remaining = text
        parsed: list[str] = []
        ordered_genres = sorted(KNOWN_GENRES, key=len, reverse=True)

        while remaining:
            matched = None
            for genre in ordered_genres:
                if remaining.startswith(genre):
                    parsed.append(genre)
                    remaining = remaining[len(genre) :]
                    matched = True
                    break

            if not matched:
                remaining = remaining[1:]

        return parsed

    def _movie_genres(self, row: pd.Series) -> list[str]:
        if "parsed_genres" in row and isinstance(row["parsed_genres"], list):
            return [str(genre) for genre in row["parsed_genres"]]
        return self._parse_genres(row.get("genres"))

    def _build_genre_based_recommendations(self, preferred_genres: list[str], top_k: int) -> list[dict[str, Any]]:
        if self.movies_df.empty or not preferred_genres:
            return []

        preferred_set = {genre for genre in preferred_genres if genre}
        if not preferred_set:
            return []

        candidates = []
        for row in self.movies_df.itertuples(index=False):
            movie_genres = self._movie_genres(pd.Series(row._asdict()))
            overlap = preferred_set.intersection(movie_genres)
            if not overlap:
                continue

            popularity = getattr(row, "popularity", 0.0)
            try:
                popularity_score = float(popularity) if pd.notna(popularity) else 0.0
            except Exception:
                popularity_score = 0.0

            overlap_score = len(overlap)
            combined_score = round(min(0.99, 0.55 + (overlap_score * 0.15) + (popularity_score * 0.25)), 4)
            candidates.append(
                {
                    "movieId": int(getattr(row, "movieId")),
                    "title": str(getattr(row, "title")),
                    "genres": movie_genres,
                    "consensus_score": combined_score,
                    "reasons": [f"Coincide con los géneros de la sala: {', '.join(sorted(overlap))}"],
                    "_overlap": overlap_score,
                    "_popularity": popularity_score,
                }
            )

        candidates.sort(key=lambda item: (-item["_overlap"], -item["_popularity"], item["title"]))
        return self._json_safe([
            {key: value for key, value in item.items() if not key.startswith("_")}
            for item in candidates[:top_k]
        ])

    def health(self) -> dict[str, Any]:
        return {
            "status": "ready" if self.is_ready() else "not_ready",
            "message": "Service ready" if self.is_ready() else "Service not ready",
            "modelLoaded": self.predictor is not None,
            "datasetLoaded": not self.movies_df.empty,
            "error": self.load_error,
        }

    def get_report(self) -> dict[str, Any]:
        if not REPORT_FILE.exists():
            raise HTTPException(status_code=404, detail="training_report.json not found")
        return json.loads(REPORT_FILE.read_text(encoding="utf-8"))

    def get_genres(self) -> list[str]:
        predictor = self._ensure_ready()
        genres = set()
        for values in self.movies_df.get("parsed_genres", pd.Series(dtype=object)).dropna().tolist():
            for genre in values:
                if genre and genre != "(no genres listed)":
                    genres.add(str(genre))
        if genres:
            return sorted(genres)

        if predictor.mlb is not None and hasattr(predictor.mlb, "classes_"):
            return [str(genre) for genre in predictor.mlb.classes_]

        return sorted(genres)

    def list_movies(self, skip: int = 0, limit: int = 20, genre: Optional[str] = None, q: Optional[str] = None) -> dict[str, Any]:
        self._ensure_ready()
        df = self.movies_df.copy()

        if q:
            df = df[df["title"].astype(str).str.contains(q, case=False, na=False)]

        if genre:
            normalized = genre.strip().lower()
            df = df[df["parsed_genres"].apply(lambda values: any(str(v).strip().lower() == normalized for v in values if str(v).strip()))]

        total = int(len(df))
        if "popularity" in df.columns:
            df = df.sort_values(by=["popularity", "title"], ascending=[False, True])
        else:
            df = df.sort_values(by=["title"], ascending=[True])

        page = df.iloc[skip : skip + limit]
        movies = [
            {
                "movieId": int(row.movieId),
                "title": str(row.title),
                "genres": [g for g in self._parse_genres(row.genres) if g and g != "(no genres listed)"],
                "popularity": float(row.popularity) if "popularity" in page.columns and pd.notna(row.popularity) else None,
            }
            for row in page.itertuples(index=False)
        ]
        return {"total": total, "skip": skip, "limit": limit, "items": movies}

    def get_movie(self, movie_id: int) -> dict[str, Any]:
        self._ensure_ready()
        match = self.movies_df[self.movies_df["movieId"] == movie_id]
        if match.empty:
            raise HTTPException(status_code=404, detail="Movie not found")
        row = match.iloc[0]
        return {
            "movieId": int(row["movieId"]),
            "title": str(row["title"]),
            "genres": [g for g in self._parse_genres(row["genres"]) if g and g != "(no genres listed)"],
            "popularity": float(row["popularity"]) if "popularity" in match.columns and pd.notna(row["popularity"]) else None,
        }

    def recommend_user(self, payload: UserRecommendationRequest) -> dict[str, Any]:
        predictor = self._ensure_ready()
        genres = payload.favoriteGenres or ([payload.favoriteGenre] if payload.favoriteGenre else [])
        recommendations = predictor.predict_for_user(
            favorite_genres=genres,
            top_k=payload.topK,
            threshold=payload.threshold,
        )
        return self._json_safe({"success": True, "count": len(recommendations), "recommendations": recommendations})

    def recommend_room(self, payload: Any) -> dict[str, Any]:
        request = self._room_request_from_payload(payload)
        return self._recommend_room_from_request(request)

    def _recommend_room_from_request(self, request: RoomRecommendationRequest) -> dict[str, Any]:
        predictor = self._ensure_ready()
        users = []
        preferred_genres: list[str] = []
        for user in request.users:
            genres = user.favoriteGenres or ([user.favoriteGenre] if user.favoriteGenre else [])
            preferred_genres.extend(genres)
            users.append({"userId": user.userId, "favoriteGenres": genres})
        genre_based = self._build_genre_based_recommendations(preferred_genres, request.topK)

        result = predictor.predict_for_room(room_users_data=users, top_k=request.topK)
        if isinstance(result, dict) and result.get("error"):
            raise HTTPException(status_code=400, detail=str(result["error"]))

        model_recommendations = result.get("recommendations", []) if isinstance(result, dict) else []
        total_users = result.get("total_users", len(users)) if isinstance(result, dict) else len(users)

        merged: list[dict[str, Any]] = []
        seen_movie_ids: set[int] = set()

        for item in genre_based + model_recommendations:
            movie_id = int(item["movieId"])
            if movie_id in seen_movie_ids:
                continue
            seen_movie_ids.add(movie_id)
            merged.append(item)
            if len(merged) >= request.topK:
                break

        return self._json_safe({
            "success": True,
            "totalUsers": total_users,
            "recommendationCount": len(merged),
            "recommendations": merged,
        })

    def create_room_poll(self, payload: Any) -> dict[str, Any]:
        request = self._room_request_from_payload(payload)
        room_recommendations = self._recommend_room_from_request(request)
        options = self._normalize_options(room_recommendations.get("recommendations", [])[:3])

        poll_id = str(uuid4())
        poll = {
            "pollId": poll_id,
            "createdAt": datetime.utcnow().isoformat(timespec="seconds") + "Z",
            "totalUsers": room_recommendations.get("totalUsers", len(request.users)),
            "options": options,
            "votes": {},
        }
        self.room_polls[poll_id] = poll
        return self._format_poll(poll)

    def get_room_poll(self, poll_id: str) -> dict[str, Any]:
        poll = self.room_polls.get(poll_id)
        if not poll:
            raise HTTPException(status_code=404, detail="Poll not found")
        return self._format_poll(poll)

    def vote_room_poll(self, poll_id: str, payload: RoomPollVoteRequest) -> dict[str, Any]:
        poll = self.room_polls.get(poll_id)
        if not poll:
            raise HTTPException(status_code=404, detail="Poll not found")

        allowed_ids = {int(option["movieId"]): option for option in poll.get("options", [])}
        if int(payload.movieId) not in allowed_ids:
            raise HTTPException(status_code=400, detail="Movie is not part of the poll options")

        poll.setdefault("votes", {})[payload.userId] = int(payload.movieId)
        return self._format_poll(poll)


app = FastAPI(
    title="MIRALO Recommendation Engine",
    version="2.0.0",
    description="FastAPI service for movie recommendations using the existing ML dataset and trained models.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

service = RecommendationService()


@app.on_event("startup")
def startup_event() -> None:
    service.reload()


@app.get("/")
def root() -> dict[str, str]:
    return {"message": "MIRALO Recommendation Engine API", "docs": "/docs"}


@app.get("/health")
def health() -> dict[str, Any]:
    payload = service.health()
    if payload["status"] != "ready":
        raise HTTPException(status_code=503, detail=payload)
    return payload


@app.get("/model/report")
def model_report() -> dict[str, Any]:
    return service.get_report()


@app.get("/genres")
def genres() -> dict[str, Any]:
    return {"count": len(service.get_genres()), "items": service.get_genres()}


@app.get("/movies")
def movies(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    genre: Optional[str] = Query(default=None),
    q: Optional[str] = Query(default=None),
) -> dict[str, Any]:
    return service.list_movies(skip=skip, limit=limit, genre=genre, q=q)


@app.get("/movies/{movie_id}")
def movie_detail(movie_id: int) -> dict[str, Any]:
    return service.get_movie(movie_id)


@app.post("/recommendations/user")
def recommendations_user(payload: UserRecommendationRequest) -> dict[str, Any]:
    return service.recommend_user(payload)


@app.post("/recommendations/room")
def recommendations_room(payload: Any = Body(...)) -> dict[str, Any]:
    return service.recommend_room(payload)


@app.post("/recommendations/room/poll")
def create_room_poll(payload: Any = Body(...)) -> dict[str, Any]:
    return service.create_room_poll(payload)


@app.get("/recommendations/room/poll/{poll_id}")
def get_room_poll(poll_id: str) -> dict[str, Any]:
    return service.get_room_poll(poll_id)


@app.post("/recommendations/room/poll/{poll_id}/vote")
def vote_room_poll(poll_id: str, payload: RoomPollVoteRequest) -> dict[str, Any]:
    return service.vote_room_poll(poll_id, payload)


# Aliases for backwards compatibility with the previous /ml routes
@app.get("/ml/health")
def ml_health() -> dict[str, Any]:
    return health()


@app.get("/ml/report")
def ml_report() -> dict[str, Any]:
    return model_report()


@app.post("/ml/predict")
def ml_predict(payload: UserRecommendationRequest) -> dict[str, Any]:
    return recommendations_user(payload)


@app.post("/ml/predict-room")
def ml_predict_room(payload: Any = Body(...)) -> dict[str, Any]:
    return recommendations_room(payload)


@app.post("/ml/predict-room/poll")
def ml_create_room_poll(payload: Any = Body(...)) -> dict[str, Any]:
    return create_room_poll(payload)


@app.post("/ml/predict-room/poll/{poll_id}/vote")
def ml_vote_room_poll(poll_id: str, payload: RoomPollVoteRequest) -> dict[str, Any]:
    return vote_room_poll(poll_id, payload)


@app.get("/ml/predict-room/poll/{poll_id}")
def ml_get_room_poll(poll_id: str) -> dict[str, Any]:
    return get_room_poll(poll_id)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=3000, reload=False)







