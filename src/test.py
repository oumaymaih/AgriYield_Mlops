import json
import joblib
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from pathlib import Path
from nettoyage_dataset import FEATURES, TARGET
from metriques import metriques_regression


def tester(root):

    root = Path(root)

    # Chemins
    test_path = root / "data" / "test.csv"
    modele_path = root / "models" / "model_v1.pkl"
    prep_path = root / "models" / "preprocessing.pkl"

    references = root / "references"
    dossier = root / "reports" / "evaluation_v1"

    references.mkdir(parents=True, exist_ok=True)
    dossier.mkdir(parents=True, exist_ok=True)

    # 1. Charger Test
    d = pd.read_csv(test_path)

    # 2. Charger modèle et preprocessing
    prep = joblib.load(prep_path)
    model = joblib.load(modele_path)

    # 3. Préparer les variables
    X_test = d[FEATURES]
    y_test = d[TARGET]

    # 4. Transformer sans fit
    X_test_transforme = prep.transform(X_test)

    # 5. Prédire Yield
    pred = model.predict(X_test_transforme)

    # 6. Calculer les métriques
    scores = metriques_regression(y_test, pred)

    # 7. Construire le rapport
    result = {
        "version": "v1",
        "modele": "model_v1.pkl",
        "preprocessing": "preprocessing.pkl",
        "algorithme": type(model).__name__,
        "ensemble": "test",
        "metriques": scores,
        "statistiques_cible": {
            "n": int(len(d)),
            "moyenne": float(y_test.mean()),
            "mediane": float(y_test.median()),
            "ecart_type": float(y_test.std()),
            "minimum": float(y_test.min()),
            "maximum": float(y_test.max())
        }
    }

    # 8. Sauvegarder les performances de référence
    chemin_performance = (
        references / "performance_v1.json"
    )

    chemin_performance.write_text(
        json.dumps(
            result,
            indent=4,
            ensure_ascii=False,
            allow_nan=False
        ),
        encoding="utf-8"
    )

    # 9. Sauvegarder les prédictions
    predictions = pd.DataFrame({
        "Yield_reel": y_test.to_numpy(),
        "Yield_predit": pred,
        "residu": y_test.to_numpy() - pred,
        "erreur_absolue": np.abs(
            y_test.to_numpy() - pred
        )
    })

    chemin_predictions = (
        dossier / "predictions_test.csv"
    )

    predictions.to_csv(
        chemin_predictions,
        index=False
    )

    # 10. Graphique réel vs prédit
    fig, ax = plt.subplots(figsize=(7, 6))

    ax.scatter(
        y_test,
        pred,
        alpha=0.4,
        s=15
    )

    minimum = min(y_test.min(), pred.min())
    maximum = max(y_test.max(), pred.max())

    ax.plot(
        [minimum, maximum],
        [minimum, maximum],
        "r--",
        label="Prédiction parfaite"
    )

    ax.set_xlabel("Yield réel")
    ax.set_ylabel("Yield prédit")
    ax.set_title("Test V1 — Réel vs Prédit")
    ax.legend()

    fig.tight_layout()

    chemin_correlation = (
        dossier / "reel_vs_predit.png"
    )

    fig.savefig(
        chemin_correlation,
        dpi=150,
        bbox_inches="tight"
    )

    plt.show()
    plt.close(fig)

    # 11. Distribution des résidus
    fig, ax = plt.subplots(figsize=(8, 4))

    ax.hist(
        y_test.to_numpy() - pred,
        bins=30,
        color="steelblue",
        edgecolor="white"
    )

    ax.axvline(
        0,
        color="red",
        linestyle="--"
    )

    ax.set_xlabel("Résidu (réel - prédit)")
    ax.set_ylabel("Effectif")
    ax.set_title("Distribution des résidus — Test V1")

    fig.tight_layout()

    chemin_residus = dossier / "residus.png"

    fig.savefig(
        chemin_residus,
        dpi=150,
        bbox_inches="tight"
    )

    plt.show()
    plt.close(fig)

    return result
