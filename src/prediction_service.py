
from pathlib import Path

import joblib
import pandas as pd

from .preprocessing_production import transformer_production


BASE_DIR = Path(__file__).resolve().parents[1]

CHEMIN_MODELE = BASE_DIR / "models" / "model_v1.pkl"
CHEMIN_PREPROCESSING = BASE_DIR / "models" / "preprocessing.pkl"


def predire_rendement(df: pd.DataFrame):
    """
    Nettoyer les observations, appliquer le prétraitement
    et calculer les prédictions du modèle V1.

    Retour :
        donnees_valides
        predictions
        avertissements
    """

    # 1. Nettoyage et prétraitement
    X_production, donnees_valides, avertissements = (
        transformer_production(
            df,
            CHEMIN_PREPROCESSING
        )
    )

    # 2. Vérifier les observations acceptées
    if X_production is None:
        return donnees_valides, [], avertissements

    # 3. Charger le modèle V1
    modele = joblib.load(CHEMIN_MODELE)

    # 4. Calculer les rendements
    predictions = modele.predict(X_production)

    return (
        donnees_valides,
        predictions.tolist(),
        avertissements
    )
