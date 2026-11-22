import json
import joblib
import pandas as pd

from pathlib import Path

from nettoyage_dataset import FEATURES, TARGET
from metriques import metriques_regression


def valider(
    root,
    version="v1",
    nom_modele=None,
    nom_preprocessing=None
):

    root = Path(root)

    # 1. Définir les fichiers de la version demandée
    if nom_modele is None:
        nom_modele = f"model_{version}.pkl"

    if nom_preprocessing is None:
        if version == "v1":
            nom_preprocessing = "preprocessing.pkl"
        else:
            nom_preprocessing = f"preprocessing_{version}.pkl"

    chemin_modele = root / "models" / nom_modele
    chemin_preprocessing = root / "models" / nom_preprocessing

    # 2. Vérifier que les fichiers existent
    if not chemin_modele.exists():
        raise FileNotFoundError(
            f"Modèle introuvable : {chemin_modele}"
        )

    if not chemin_preprocessing.exists():
        raise FileNotFoundError(
            f"Preprocessing introuvable : {chemin_preprocessing}"
        )

    # 3. Charger Validation
    validation = pd.read_csv(
        root / "data" / "validation.csv"
    )

    # 4. Charger le preprocessing et le modèle
    preprocessor = joblib.load(chemin_preprocessing)
    model = joblib.load(chemin_modele)

    # 5. Transformer Validation sans fit
    X_validation = preprocessor.transform(
        validation[FEATURES]
    )

    y_validation = validation[TARGET]

    # 6. Prédire Yield
    predictions = model.predict(X_validation)

    # 7. Calculer les métriques
    scores = metriques_regression(
        y_validation,
        predictions
    )

    # 8. Préparer le rapport
    resultat = {
        "version": version,
        "modele": nom_modele,
        "preprocessing": nom_preprocessing,
        "algorithme": type(model).__name__,
        "ensemble": "validation",
        "metriques": scores,
        "note": "Régression : R2, MAE et RMSE"
    }

    # 9. Sauvegarder le rapport JSON
    chemin_rapport = (
        root / "references" / f"validation_{version}.json"
    )

    chemin_rapport.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    chemin_rapport.write_text(
        json.dumps(
            resultat,
            indent=4,
            ensure_ascii=False
        ),
        encoding="utf-8"
    )

    return resultat
