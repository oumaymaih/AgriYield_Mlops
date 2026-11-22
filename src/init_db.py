
from pathlib import Path

from sqlalchemy import select, text

from src.database import Base, engine, SessionLocal
from src.db_models import ModelVersion

ROOT = Path(__file__).resolve().parent.parent


def initialiser_base():
    # 1. Vérifier la connexion à MariaDB
    with engine.connect() as connexion:
        connexion.execute(text("SELECT 1"))

    print("Connexion MariaDB réussie.")

    # 2. Créer uniquement les tables manquantes
    Base.metadata.create_all(bind=engine)

    print("Les 8 tables sont prêtes.")

    # 3. Vérifier les fichiers du modèle V1
    modele = ROOT / "models" / "model_v1.pkl"
    preprocessing = ROOT / "models" / "preprocessing.pkl"

    if not modele.is_file() or not preprocessing.is_file():
        raise FileNotFoundError(
            "Vérifiez models/model_v1.pkl et "
            "models/preprocessing.pkl"
        )

    # 4. Enregistrer V1 uniquement s'il n'existe pas
    with SessionLocal() as session:
        v1 = session.scalar(
            select(ModelVersion).where(
                ModelVersion.version == "V1"
            )
        )

        if v1 is None:
            v1 = ModelVersion(
                version="V1",
                chemin_modele="models/model_v1.pkl",
                chemin_preprocessing="models/preprocessing.pkl",
                statut="active"
            )

            session.add(v1)
            session.commit()

            print("Modèle V1 enregistré comme modèle actif.")
        else:
            print("Le modèle V1 existe déjà.")

    print("Initialisation terminée.")


if __name__ == "__main__":
    initialiser_base()
