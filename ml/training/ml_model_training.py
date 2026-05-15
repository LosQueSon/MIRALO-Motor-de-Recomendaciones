#!/usr/bin/env python3
"""
MIRALO Machine Learning Model Training Script
Entrena un modelo XGBoost basado en géneros para predecir preferencias de películas
"""

import pandas as pd
import numpy as np
import json
import joblib
from datetime import datetime
from pathlib import Path
import os

# ML Libraries
from sklearn.preprocessing import MultiLabelBinarizer
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    confusion_matrix,
    classification_report,
    roc_auc_score
)
import xgboost as xgb

# ==================== CONFIGURACIÓN ====================
# Ajustar rutas: el script vive en ml/training/, pero los datos estarán en <repo_root>/data
# y los modelos en <repo_root>/ml_models
ROOT_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT_DIR / "data"
MOVIES_FILE = DATA_DIR / "movies.csv"
RATINGS_FILE = DATA_DIR / "ratings.csv"
OUTPUT_DIR = ROOT_DIR / "ml_models"
RATING_THRESHOLD = 3.5
TEST_SIZE = 0.2
RANDOM_STATE = 42

# ==================== FUNCIONES AUXILIARES ====================

def load_and_preprocess_data():
    """
    Carga y preprocesa los datos de películas y ratings
    """
    print("[PASO 1] Cargando datos...")

    # Cargar películas
    movies_df = pd.read_csv(MOVIES_FILE)
    print(f"✓ Películas cargadas: {len(movies_df)} películas")

    # Cargar ratings
    ratings_df = pd.read_csv(RATINGS_FILE)
    print(f"✓ Ratings cargados: {len(ratings_df)} ratings")

    # Merge
    print("\n[PASO 2] Uniendo datasets...")
    data = ratings_df.merge(movies_df, on='movieId', how='inner')
    print(f"✓ Datasets unidos: {len(data)} registros")

    # Crear variable binaria de like/dislike
    print("\n[PASO 3] Binearizando ratings...")
    data['liked'] = (data['rating'] >= RATING_THRESHOLD).astype(int)
    print(f"✓ Like (≥{RATING_THRESHOLD}): {data['liked'].sum()} | Dislike: {(1-data['liked']).sum()}")

    # Procesar géneros (split por |)
    print("\n[PASO 4] Procesando géneros...")
    data['genres_list'] = data['genres'].str.split('|')

    # One-Hot Encoding
    mlb = MultiLabelBinarizer()
    genres_encoded = mlb.fit_transform(data['genres_list'])
    genres_df = pd.DataFrame(genres_encoded, columns=mlb.classes_, index=data.index)

    print(f"✓ Géneros únicos: {len(mlb.classes_)}")
    print(f"  {', '.join(mlb.classes_)}")

    return data, genres_df, mlb


def train_models(X_train, X_test, y_train, y_test, genres_feature_names):
    """
    Entrena Random Forest y XGBoost
    """
    print("\n[PASO 5] Entrenando modelos...")

    # Random Forest
    print("  - Entrenando Random Forest...")
    rf_model = RandomForestClassifier(
        n_estimators=100,
        max_depth=15,
        random_state=RANDOM_STATE,
        n_jobs=-1
    )
    rf_model.fit(X_train, y_train)
    print("  ✓ Random Forest entrenado")

    # XGBoost
    print("  - Entrenando XGBoost...")
    xgb_model = xgb.XGBClassifier(
        n_estimators=100,
        max_depth=7,
        learning_rate=0.1,
        random_state=RANDOM_STATE,
        n_jobs=-1,
        eval_metric='logloss'
    )
    xgb_model.fit(X_train, y_train)
    print("  ✓ XGBoost entrenado")

    return rf_model, xgb_model


def evaluate_model(model, X_train, X_test, y_train, y_test, model_name):
    """
    Evalúa un modelo y retorna métricas
    """
    print(f"\n[EVALUACIÓN] {model_name}")
    print("-" * 60)

    # Predicciones
    y_train_pred = model.predict(X_train)
    y_test_pred = model.predict(X_test)

    # Probabilidades para AUC
    if hasattr(model, 'predict_proba'):
        y_test_proba = model.predict_proba(X_test)[:, 1]
        auc_score = roc_auc_score(y_test, y_test_proba)
    else:
        auc_score = None

    # Métricas
    metrics = {
        'model_name': model_name,
        'train_accuracy': accuracy_score(y_train, y_train_pred),
        'test_accuracy': accuracy_score(y_test, y_test_pred),
        'precision': precision_score(y_test, y_test_pred, zero_division=0),
        'recall': recall_score(y_test, y_test_pred, zero_division=0),
        'f1': f1_score(y_test, y_test_pred, zero_division=0),
        'auc': auc_score,
        'confusion_matrix': confusion_matrix(y_test, y_test_pred).tolist(),
        'classification_report': classification_report(y_test, y_test_pred, output_dict=True)
    }

    # Mostrar métricas
    print(f"Train Accuracy:  {metrics['train_accuracy']:.4f}")
    print(f"Test Accuracy:   {metrics['test_accuracy']:.4f}")
    print(f"Precision:       {metrics['precision']:.4f}")
    print(f"Recall:          {metrics['recall']:.4f}")
    print(f"F1-Score:        {metrics['f1']:.4f}")
    if auc_score:
        print(f"AUC-ROC:         {auc_score:.4f}")

    # Matriz de confusión
    cm = np.array(metrics['confusion_matrix'])
    print(f"\nMatriz de Confusión:")
    print(f"  [{cm[0,0]:5d}  {cm[0,1]:5d}]   [TN  FP]")
    print(f"  [{cm[1,0]:5d}  {cm[1,1]:5d}]   [FN  TP]")

    return metrics


def save_model(model, model_name):
    """
    Guarda el modelo en formato joblib
    """
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    model_path = OUTPUT_DIR / f"{model_name}.joblib"
    joblib.dump(model, str(model_path))
    print(f"✓ Modelo guardado: {model_path}")

    return str(model_path)


def generate_report(all_metrics, genres_feature_names, X_train, X_test, y_train, y_test):
    """
    Genera un reporte completo en JSON
    """
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    report = {
        'timestamp': datetime.now().isoformat(),
        'dataset_info': {
            'movies_total': len(pd.read_csv(MOVIES_FILE)),
            'ratings_total': len(pd.read_csv(RATINGS_FILE)),
            'training_samples': len(X_train),
            'test_samples': len(X_test),
            'positive_class_ratio': float(y_train.sum() / len(y_train)),
            'test_positive_ratio': float(y_test.sum() / len(y_test)),
            'genres_count': len(genres_feature_names),
            'rating_threshold': RATING_THRESHOLD
        },
        'models_metrics': all_metrics,
        'genre_features': genres_feature_names.tolist()
    }

    report_path = OUTPUT_DIR / "training_report.json"
    with open(report_path, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    print(f"\n✓ Reporte guardado: {report_path}")
    return report


def main():
    """
    Flujo principal del entrenamiento
    """
    print("=" * 60)
    print("MIRALO ML MODEL TRAINING")
    print("=" * 60)

    # Cargar y preprocesar
    data, genres_df, mlb = load_and_preprocess_data()

    # Preparar features y target
    print("\n[PASO 6] Preparando features y target...")
    X = genres_df.values
    y = data['liked'].values

    print(f"✓ Shape X: {X.shape}")
    print(f"✓ Shape y: {y.shape}")

    # Train-Test Split
    print("\n[PASO 7] Dividiendo en train (80%) y test (20%)...")
    X_train, X_test, y_train, y_test = train_test_split(
        X, y,
        test_size=TEST_SIZE,
        random_state=RANDOM_STATE,
        stratify=y
    )

    print(f"✓ Train: {len(X_train)} muestras")
    print(f"✓ Test:  {len(X_test)} muestras")

    # Entrenar modelos
    rf_model, xgb_model = train_models(X_train, X_test, y_train, y_test, mlb.classes_)

    # Evaluar modelos
    rf_metrics = evaluate_model(rf_model, X_train, X_test, y_train, y_test, "Random Forest")
    xgb_metrics = evaluate_model(xgb_model, X_train, X_test, y_train, y_test, "XGBoost")

    # Guardar modelos
    print("\n[PASO 8] Guardando modelos...")
    rf_path = save_model(rf_model, "rf_recommender_model")
    xgb_path = save_model(xgb_model, "xgb_recommender_model")

    # Guardar MLBinarizer (necesario para predicciones futuras)
    mlb_path = OUTPUT_DIR / "mlb_genres.joblib"
    joblib.dump(mlb, str(mlb_path))
    print(f"✓ MultiLabelBinarizer guardado: {mlb_path}")

    # Generar reporte
    print("\n[PASO 9] Generando reporte...")
    report = generate_report(
        [rf_metrics, xgb_metrics],
        mlb.classes_,
        X_train, X_test, y_train, y_test
    )

    # Resumen final
    print("\n" + "=" * 60)
    print("RESUMEN FINAL")
    print("=" * 60)
    print(f"\n📊 MEJOR MODELO: XGBoost")
    print(f"   Accuracy:  {xgb_metrics['test_accuracy']:.4f}")
    print(f"   F1-Score:  {xgb_metrics['f1']:.4f}")
    print(f"\n📁 Archivos generados:")
    print(f"   - {rf_path}")
    print(f"   - {xgb_path}")
    print(f"   - {mlb_path}")
    print(f"   - {OUTPUT_DIR / 'training_report.json'}")
    print("\n✓ ¡Entrenamiento completado!")


if __name__ == "__main__":
    main()
