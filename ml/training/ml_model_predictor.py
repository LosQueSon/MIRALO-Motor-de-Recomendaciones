#!/usr/bin/env python3
"""
MIRALO Model Prediction Service
Servicio para hacer predicciones con el modelo entrenado
"""

import json
import joblib
from pathlib import Path
from typing import Dict, List, Tuple
import numpy as np
from dataclasses import dataclass, asdict

# ==================== CONFIGURACIÓN ====================
# Ajustar rutas: este script está en ml/training/, los datos están en <repo_root>/data
ROOT_DIR = Path(__file__).resolve().parents[2]
MODEL_DIR = ROOT_DIR / "ml_models"
MODEL_FILE = MODEL_DIR / "xgb_recommender_model.joblib"
MLB_FILE = MODEL_DIR / "mlb_genres.joblib"
MOVIES_FILE = ROOT_DIR / "data" / "movies.csv"
RATINGS_FILE = ROOT_DIR / "data" / "ratings.csv"

@dataclass
class PredictionResult:
    """Resultado de predicción para una película"""
    movieId: int
    title: str
    predicted_probability: float
    liked: bool
    genres: List[str]
    reason: str


class MiraloMLPredictor:
    """
    Servicio de predicción para MIRALO
    """

    def __init__(self, model_path=None, mlb_path=None):
        """
        Inicializa el predictor cargando el modelo y el binarizador
        """
        self.model_path = model_path or MODEL_FILE
        self.mlb_path = mlb_path or MLB_FILE
        self.model = None
        self.mlb = None
        self.movies_df = None
        self._load_models()

    def _load_models(self):
        """
        Carga el modelo entrenado y el MultiLabelBinarizer
        """
        try:
            self.model = joblib.load(str(self.model_path))
            self.mlb = joblib.load(str(self.mlb_path))
            # NO IMPRIMIR NADA AQUI - Contamina stdout
        except FileNotFoundError as e:
            raise FileNotFoundError(
                f"Modelo no encontrado. Primero ejecuta ml_model_training.py\n{e}"
            )

    def load_movies(self, movies_file=None):
        """
        Carga el CSV de películas
        """
        try:
            import pandas as pd
            file = movies_file or MOVIES_FILE
            self.movies_df = pd.read_csv(file)

            # Intentar cargar ratings para calcular una métrica de popularidad (fallback)
            try:
                ratings_df = pd.read_csv(RATINGS_FILE)
                # Popularidad: promedio de rating por película (si existe)
                pop = ratings_df.groupby('movieId')['rating'].mean().rename('popularity')
                pop = (pop - pop.min()) / (pop.max() - pop.min())
                self.movies_df = self.movies_df.merge(pop, left_on='movieId', right_index=True, how='left')
                self.movies_df['popularity'] = self.movies_df['popularity'].fillna(0.0)
            except Exception:
                # Si no hay ratings disponibles, establecer popularidad a 0
                self.movies_df['popularity'] = 0.0
            # NO IMPRIMIR NADA AQUI - Contamina stdout
        except ImportError:
            raise ImportError("pandas es requerido para esta funcionalidad")

    def predict_for_user(
        self,
        favorite_genres: List[str],
        top_k: int = 10,
        threshold: float = 0.5
    ) -> List[Dict]:
        """
        Genera predicciones para un usuario basado en sus géneros favoritos

        Args:
            favorite_genres: Lista de géneros favoritos del usuario
            top_k: Número de recomendaciones a devolver
            threshold: Umbral de probabilidad (0-1)

        Returns:
            Lista de recomendaciones ordenadas por probabilidad
        """
        if not self.model or not self.mlb:
            raise RuntimeError("Modelo no cargado. Ejecuta _load_models() primero")

        # Verificar que las películas están cargadas
        if self.movies_df is None:
            raise RuntimeError("Películas no cargadas. Ejecuta load_movies() primero")

        # Validar géneros
        favorite_genres = [g.strip() for g in favorite_genres]
        unknown_genres = set(favorite_genres) - set(self.mlb.classes_)
        if unknown_genres:
            print(f"[WARNING] Generos desconocidos: {unknown_genres}")
            favorite_genres = [g for g in favorite_genres if g not in unknown_genres]

        if not favorite_genres:
            # Fallback: recomendar por popularidad cuando no hay géneros válidos
            # Ordenar por columna 'popularity' si existe
            if 'popularity' in self.movies_df.columns:
                top = self.movies_df.sort_values('popularity', ascending=False).head(top_k)
                results = []
                for _, row in top.iterrows():
                    prob = float(row.get('popularity', 0.0))
                    results.append({
                        'movieId': int(row['movieId']),
                        'title': row['title'],
                        'genres': row['genres'].split('|') if isinstance(row['genres'], str) else [],
                        'predicted_probability': prob,
                        'liked': prob >= threshold,
                        'reason': 'No se proporcionaron géneros conocidos. Recomendado por popularidad.'
                    })
                return results
            else:
                return []

        print(f"\n[INFO] Prediciendo para generos: {favorite_genres}")

        # Preparar features para todas las películas
        predictions = []

        for _, row in self.movies_df.iterrows():
            movie_genres = row['genres'].split('|')

            # One-Hot Encoding de los géneros de la película
            movie_encoded = self.mlb.transform([movie_genres])

            # Predicción
            prob = self.model.predict_proba(movie_encoded)[0][1]  # Probabilidad de "Like"

            # Filtrar por threshold
            if prob >= threshold:
                # Calcular razón de recomendación
                matching_genres = set(movie_genres) & set(favorite_genres)
                inferred_genres = set(movie_genres) - set(favorite_genres)

                reason = self._generate_reason(
                    favorite_genres,
                    matching_genres,
                    inferred_genres,
                    prob
                )

                predictions.append({
                    'movieId': int(row['movieId']),
                    'title': row['title'],
                    'genres': movie_genres,
                    'predicted_probability': float(prob),
                    'liked': prob >= 0.5,
                    'reason': reason
                })

        # Ordenar por probabilidad y devolver top_k
        predictions.sort(key=lambda x: x['predicted_probability'], reverse=True)

        print(f"[OK] {len(predictions)} peliculas encontradas")
        return predictions[:top_k]

    def predict_for_room(self, room_users_data: List[Dict], top_k: int = 10):
        """
        Predice para un grupo de usuarios (sala)

        Args:
            room_users_data: Lista de dicts con 'userId' y 'favoriteGenres'
            top_k: Top N recomendaciones

        Returns:
            Recomendaciones consensuadas para la sala
        """
        if not room_users_data:
            return {'error': 'No users provided'}

        all_predictions = []

        # Obtener predicciones para cada usuario
        for user_data in room_users_data:
            user_id = user_data.get('userId')
            favorite_genres = user_data.get('favoriteGenres', [])

            user_predictions = self.predict_for_user(
                favorite_genres,
                top_k=100,  # Obtener más para el consensus
                threshold=0.3
            )

            for pred in user_predictions:
                pred['user_id'] = user_id

            all_predictions.extend(user_predictions)

        # Consensus: agrupar por película y promediar scores
        if not all_predictions:
            return {
                'total_users': len(room_users_data),
                'recommendations': []
            }

        import pandas as pd
        df = pd.DataFrame(all_predictions)

        grouped = df.groupby('movieId').agg({
            'title': 'first',
            'genres': 'first',
            'predicted_probability': 'mean',
            'reason': lambda x: list(set(x))
        }).reset_index()

        grouped = grouped.sort_values('predicted_probability', ascending=False)

        results = []
        for _, row in grouped.head(top_k).iterrows():
            results.append({
                'movieId': int(row['movieId']),
                'title': row['title'],
                'genres': row['genres'],
                'consensus_score': float(row['predicted_probability']),
                'reasons': row['reason']
            })

        return {
            'total_users': len(room_users_data),
            'recommendations': results
        }

    def _generate_reason(
        self,
        favorite_genres: List[str],
        matching_genres: set,
        inferred_genres: set,
        probability: float
    ) -> str:
        """
        Genera una explicación legible para la recomendación
        """
        if matching_genres:
            matched = ', '.join(matching_genres)
            if inferred_genres:
                inferred = ', '.join(list(inferred_genres)[:2])
                return f"Coincide con tus géneros favoritos ({matched}) y está relacionado con {inferred}"
            else:
                return f"Coincide con tus géneros favoritos: {matched}"
        elif inferred_genres:
            inferred = ', '.join(list(inferred_genres)[:2])
            return f"Relacionado con tus géneros: {inferred} (confianza: {probability:.0%})"
        else:
            return f"Predicción basada en tu perfil de géneros (confianza: {probability:.0%})"


def main_example():
    """
    Ejemplo de uso del predictor
    """
    print("=" * 60)
    print("MIRALO ML PREDICTOR - EJEMPLO")
    print("=" * 60)

    # Inicializar predictor
    predictor = MiraloMLPredictor()
    predictor.load_movies()

    # Ejemplo 1: Usuario individual
    print("\n[EJEMPLO 1] Prediccion para usuario individual")
    user_genres = ['Action', 'Sci-Fi', 'Adventure']
    predictions = predictor.predict_for_user(user_genres, top_k=5)

    print(f"\nTop 5 peliculas para {user_genres}:")
    for i, pred in enumerate(predictions, 1):
        print(f"{i}. {pred['title']} ({pred['predicted_probability']:.0%})")
        print(f"   {pred['reason']}")

    # Ejemplo 2: Sala con múltiples usuarios
    print("\n\n[EJEMPLO 2] Prediccion para sala (grupo de usuarios)")
    room_data = [
        {'userId': 'user1', 'favoriteGenres': ['Action', 'Thriller']},
        {'userId': 'user2', 'favoriteGenres': ['Sci-Fi', 'Adventure']},
        {'userId': 'user3', 'favoriteGenres': ['Action', 'Adventure']}
    ]

    room_predictions = predictor.predict_for_room(room_data, top_k=5)

    print(f"\nRecomendaciones de consenso para sala ({room_predictions['total_users']} usuarios):")
    for i, pred in enumerate(room_predictions['recommendations'], 1):
        print(f"{i}. {pred['title']} (consenso: {pred['consensus_score']:.0%})")
        if pred['reasons']:
            print(f"   Razones: {pred['reasons'][0]}")


if __name__ == "__main__":
    main_example()







