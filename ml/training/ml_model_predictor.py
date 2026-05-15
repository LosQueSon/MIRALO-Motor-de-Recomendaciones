#!/usr/bin/env python3
from __future__ import annotations

import joblib
from pathlib import Path
from typing import Dict, List, Optional
import numpy as np
from dataclasses import dataclass

ROOT_DIR = Path(__file__).resolve().parents[2]
MODEL_DIR = ROOT_DIR / "ml_models"
MODEL_FILE = MODEL_DIR / "xgb_recommender_model.joblib"
MLB_FILE = MODEL_DIR / "mlb_genres.joblib"
MOVIES_FILE = ROOT_DIR / "data" / "movies.csv"


@dataclass
class PredictionResult:
    movieId: int
    title: str
    predicted_probability: float
    liked: bool
    genres: List[str]
    reason: str


class MiraloMLPredictor:
    def __init__(self, model_path=None, mlb_path=None):
        self.model_path = model_path or MODEL_FILE
        self.mlb_path = mlb_path or MLB_FILE
        self.model = None
        self.mlb = None
        self.movies_df = None
        # Pre-computed at load_movies() time — never recomputed per-request
        self.probs_all: Optional[np.ndarray] = None
        self.sorted_indices: Optional[np.ndarray] = None
        self._movie_ids: Optional[np.ndarray] = None
        self._movie_titles: Optional[np.ndarray] = None
        self._movie_genres_raw: Optional[np.ndarray] = None
        self._load_models()

    def _load_models(self):
        try:
            self.model = joblib.load(str(self.model_path))
            self.mlb = joblib.load(str(self.mlb_path))
        except FileNotFoundError as e:
            raise FileNotFoundError(
                f"Modelo no encontrado. Primero ejecuta ml_model_training.py\n{e}"
            )

    def load_movies(self, movies_file=None):
        import pandas as pd
        file = movies_file or MOVIES_FILE
        self.movies_df = pd.read_csv(file)
        # Popularity is pre-computed in movies.csv (via training pipeline).
        # If the column is absent, default to 0 — ratings.csv is NOT loaded at
        # runtime to keep startup memory low on the Azure Basic plan.
        if "popularity" not in self.movies_df.columns:
            self.movies_df["popularity"] = 0.0
        self.movies_df["popularity"] = self.movies_df["popularity"].fillna(0.0)

        # Pre-compute the full feature matrix and probabilities once.
        # The XGBoost model predicts purely from movie genres, so scores are
        # request-independent — no need to run inference per-request.
        all_genres = [
            g.split("|") if isinstance(g, str) else []
            for g in self.movies_df["genres"]
        ]
        X_all = self.mlb.transform(all_genres)
        self.probs_all = self.model.predict_proba(X_all)[:, 1]
        # Sort descending once; predict_for_user just iterates until threshold
        self.sorted_indices = np.argsort(self.probs_all)[::-1]

        # Cache numpy arrays for zero-overhead row access in hot path
        self._movie_ids = self.movies_df["movieId"].values
        self._movie_titles = self.movies_df["title"].values
        self._movie_genres_raw = self.movies_df["genres"].values

    def predict_for_user(
        self,
        favorite_genres: List[str],
        top_k: int = 10,
        threshold: float = 0.5,
    ) -> List[Dict]:
        if self.model is None or self.mlb is None or self.movies_df is None:
            raise RuntimeError("Modelo o películas no cargados")

        valid_classes = set(self.mlb.classes_)
        favorite_genres = [g.strip() for g in favorite_genres if g.strip() in valid_classes]

        if not favorite_genres:
            # Fallback: top movies by pre-normalised popularity score
            top_idx = np.argsort(self.movies_df["popularity"].values)[::-1][:top_k]
            results = []
            for idx in top_idx:
                pop = float(self.movies_df["popularity"].iloc[idx])
                genres = str(self._movie_genres_raw[idx]).split("|")
                results.append({
                    "movieId": int(self._movie_ids[idx]),
                    "title": str(self._movie_titles[idx]),
                    "genres": genres,
                    "predicted_probability": pop,
                    "liked": False,
                    "reason": "No se proporcionaron géneros conocidos. Recomendado por popularidad.",
                })
            return results

        fav_set = set(favorite_genres)
        results: List[Dict] = []

        # sorted_indices is pre-sorted descending by probability — iterate until
        # threshold is no longer met or we have enough results (O(top_k) typical case)
        for idx in self.sorted_indices:
            prob = float(self.probs_all[idx])
            if prob < threshold:
                break
            if len(results) >= top_k:
                break
            genres_raw = self._movie_genres_raw[idx]
            genres = genres_raw.split("|") if isinstance(genres_raw, str) else []
            matching = set(genres) & fav_set
            inferred = set(genres) - fav_set
            results.append({
                "movieId": int(self._movie_ids[idx]),
                "title": str(self._movie_titles[idx]),
                "genres": genres,
                "predicted_probability": prob,
                "liked": prob >= 0.5,
                "reason": self._generate_reason(favorite_genres, matching, inferred, prob),
            })

        return results

    def predict_for_room(self, room_users_data: List[Dict], top_k: int = 10):
        if not room_users_data:
            return {"error": "No users provided"}

        all_predictions = []
        for user_data in room_users_data:
            user_id = user_data.get("userId")
            favorite_genres = user_data.get("favoriteGenres", [])
            user_preds = self.predict_for_user(
                favorite_genres, top_k=100, threshold=0.3
            )
            for pred in user_preds:
                pred["user_id"] = user_id
            all_predictions.extend(user_preds)

        if not all_predictions:
            return {"total_users": len(room_users_data), "recommendations": []}

        import pandas as pd
        df = pd.DataFrame(all_predictions)
        grouped = (
            df.groupby("movieId")
            .agg(
                title=("title", "first"),
                genres=("genres", "first"),
                predicted_probability=("predicted_probability", "mean"),
                reason=("reason", lambda x: list(set(x))),
            )
            .reset_index()
            .sort_values("predicted_probability", ascending=False)
        )

        results = [
            {
                "movieId": int(row["movieId"]),
                "title": row["title"],
                "genres": row["genres"],
                "consensus_score": float(row["predicted_probability"]),
                "reasons": row["reason"],
            }
            for _, row in grouped.head(top_k).iterrows()
        ]
        return {"total_users": len(room_users_data), "recommendations": results}

    def _generate_reason(self, favorite_genres, matching_genres, inferred_genres, probability):
        if matching_genres:
            matched = ", ".join(matching_genres)
            if inferred_genres:
                inferred = ", ".join(list(inferred_genres)[:2])
                return f"Coincide con tus géneros favoritos ({matched}) y está relacionado con {inferred}"
            return f"Coincide con tus géneros favoritos: {matched}"
        if inferred_genres:
            inferred = ", ".join(list(inferred_genres)[:2])
            return f"Relacionado con tus géneros: {inferred} (confianza: {probability:.0%})"
        return f"Predicción basada en tu perfil de géneros (confianza: {probability:.0%})"


if __name__ == "__main__":
    predictor = MiraloMLPredictor()
    predictor.load_movies()
    preds = predictor.predict_for_user(["Action", "Sci-Fi"], top_k=5)
    for p in preds:
        print(f"{p['title']} ({p['predicted_probability']:.0%}) — {p['reason']}")
