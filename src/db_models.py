
from sqlalchemy import (
    Column, Integer, String, Float, DateTime,
    ForeignKey, Text, JSON, UniqueConstraint
)
from sqlalchemy.sql import func

from src.database import Base


# 1. Versions des modèles
class ModelVersion(Base):
    __tablename__ = "model_versions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    version = Column(String(20), unique=True, nullable=False)
    date_entrainement = Column(DateTime, nullable=True)

    mae = Column(Float, nullable=True)
    rmse = Column(Float, nullable=True)
    r2 = Column(Float, nullable=True)

    chemin_modele = Column(String(255), nullable=False)
    chemin_preprocessing = Column(String(255), nullable=False)

    statut = Column(String(30), nullable=False, default="candidate")


# 2. Lots de données
class Lot(Base):
    __tablename__ = "lots"

    id = Column(Integer, primary_key=True, autoincrement=True)
    nom_lot = Column(String(150), nullable=True)
    date_import = Column(DateTime, server_default=func.now())

    source = Column(String(30), nullable=False, default="production")
    nombre_lignes = Column(Integer, default=0)


# 3. Observations agricoles
class Observation(Base):
    __tablename__ = "observations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    lot_id = Column(Integer, ForeignKey("lots.id"), nullable=True)

    date_observation = Column(DateTime, server_default=func.now())

    Crop = Column(String(100), nullable=True)
    Season = Column(String(100), nullable=True)
    State = Column(String(100), nullable=True)
    Crop_Year = Column(Integer, nullable=True)

    Area = Column(Float, nullable=True)
    Annual_Rainfall = Column(Float, nullable=True)
    Fertilizer = Column(Float, nullable=True)
    Pesticide = Column(Float, nullable=True)

    rendement_reel = Column(Float, nullable=True)


# 4. Prédictions
class Prediction(Base):
    __tablename__ = "predictions"

    id = Column(Integer, primary_key=True, autoincrement=True)

    observation_id = Column(
        Integer, ForeignKey("observations.id"), nullable=False
    )
    model_version_id = Column(
        Integer, ForeignKey("model_versions.id"), nullable=False
    )

    rendement_predit = Column(Float, nullable=False)
    date_prediction = Column(DateTime, server_default=func.now())


# 5. Exécutions de surveillance
class MonitoringRun(Base):
    __tablename__ = "monitoring_runs"

    id = Column(Integer, primary_key=True, autoincrement=True)

    model_version_id = Column(
        Integer, ForeignKey("model_versions.id"), nullable=False
    )
    lot_id = Column(Integer, ForeignKey("lots.id"), nullable=True)

    date_analyse = Column(DateTime, server_default=func.now())
    periode_debut = Column(DateTime, nullable=True)
    periode_fin = Column(DateTime, nullable=True)

    type_analyse = Column(String(30), nullable=False)
    statut = Column(String(30), default="en_cours")


# 6. Résultats de surveillance Evidently
class MonitoringResult(Base):
    __tablename__ = "monitoring_results"

    id = Column(Integer, primary_key=True, autoincrement=True)

    monitoring_run_id = Column(
        Integer,
        ForeignKey("monitoring_runs.id"),
        nullable=False,
        unique=True
    )

    nombre_observations = Column(Integer, nullable=True)
    nombre_variables_derive = Column(Integer, nullable=True)
    pourcentage_drift = Column(Float, nullable=True)

    mae = Column(Float, nullable=True)
    rmse = Column(Float, nullable=True)
    r2 = Column(Float, nullable=True)

    # Résultats détaillés Evidently pour le dashboard
    details_json = Column(JSON, nullable=True)


# 7. Alertes
class Alerte(Base):
    __tablename__ = "alertes"

    id = Column(Integer, primary_key=True, autoincrement=True)

    monitoring_run_id = Column(
        Integer, ForeignKey("monitoring_runs.id"), nullable=False
    )

    type_alerte = Column(String(30), nullable=False)
    severite = Column(String(20), nullable=False)

    description = Column(Text, nullable=True)
    statut = Column(String(30), default="active")

    date_creation = Column(DateTime, server_default=func.now())


# 8. Historique des réentraînements
class RetrainingRun(Base):
    __tablename__ = "retraining_runs"

    id = Column(Integer, primary_key=True, autoincrement=True)

    model_version_id = Column(
        Integer, ForeignKey("model_versions.id"), nullable=True
    )

    date_debut = Column(DateTime, server_default=func.now())
    date_fin = Column(DateTime, nullable=True)

    statut = Column(String(30), default="en_cours")

    mae_v2 = Column(Float, nullable=True)
    rmse_v2 = Column(Float, nullable=True)
    r2_v2 = Column(Float, nullable=True)

    decision = Column(String(100), nullable=True)
