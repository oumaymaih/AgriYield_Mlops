import json
import joblib
import hashlib
import pandas as pd

from pathlib import Path
from sklearn.ensemble import GradientBoostingRegressor
from nettoyage_dataset import FEATURES, TARGET


def entrainer(root):

    root = Path(root)

    # Charger les données Train
    data_path = root / "data" / "train.csv"
    train = pd.read_csv(data_path)

    # Charger le preprocessing déjà entraîné
    preprocessing_path = root / "models" / "preprocessing.pkl"

    preprocessor = joblib.load(preprocessing_path)

    # Appliquer les transformations sans réapprentissage
    X_train = preprocessor.transform(train[FEATURES])
    y_train = train[TARGET]

    # Création du modèle Gradient Boosting
    model = GradientBoostingRegressor(
        n_estimators=100,
        learning_rate=0.1,
        max_depth=3,
        random_state=42
    )

    # Entraînement exclusivement sur Train
    model.fit(X_train, y_train)

    # Sauvegarde du modèle
    model_path = root / "models" / "model_v1.pkl"
    joblib.dump(model, model_path)

    # Configuration et traçabilité
    config = {
        "version": "V1",
        "type": "regression",
        "algorithme": "GradientBoostingRegressor",
        "parametres": {
            "n_estimators": 100,
            "learning_rate": 0.1,
            "max_depth": 3,
            "random_state": 42
        },
        "cible": TARGET,
        "features": FEATURES,
        "train_sha256": hashlib.sha256(
            data_path.read_bytes()
        ).hexdigest(),
        "preprocessing": "preprocessing.pkl",
        "modele": "model_v1.pkl"
    }

    config_path = (
        root / "references" / "config_model_v1.json"
    )

    config_path.write_text(
        json.dumps(
            config,
            indent=2,
            ensure_ascii=False
        ),
        encoding="utf-8"
    )

    return model, preprocessor
