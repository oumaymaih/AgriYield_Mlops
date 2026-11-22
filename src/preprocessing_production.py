
import joblib

from pathlib import Path
from .nettoyage_production import nettoyer_production


def transformer_production(df, chemin_pkl):

    # 1. Valider et nettoyer les nouvelles données
    donnees_valides, avertissements = (
        nettoyer_production(df)
    )

    # 2. Vérifier s'il existe des observations valides
    if donnees_valides.empty:
        return None, donnees_valides, avertissements

    # 3. Charger le preprocessing appris sur Train
    preprocessor = joblib.load(Path(chemin_pkl))

    # 4. Appliquer les transformations sans réapprentissage
    X_production = preprocessor.transform(
        donnees_valides
    )

    # 5. Retourner les données transformées,
    # les données nettoyées et les avertissements
    return X_production, donnees_valides, avertissements
