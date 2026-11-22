
# =====================================================
# AGRIYIELD MLOPS - API PRINCIPALE
# Fichier : api/main.py
# =====================================================

# =====================================================
# 1. IMPORTS
# =====================================================

import io
import os
import math
import tempfile

from pathlib import Path

import pandas as pd
from datetime import date, datetime
from typing import Optional

from fastapi import Body
from sqlalchemy import func
from sqlalchemy.inspection import inspect

from src.db_models import Prediction

from fastapi import (
    FastAPI,
    Request,
    HTTPException,
    UploadFile,
    File
)

from fastapi.responses import (
    HTMLResponse,
    FileResponse
)

from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from sqlalchemy import select

from api.schemas import (
    ObservationSchema,
    COLONNES_ATTENDUES
)

from src.prediction_service import predire_rendement
from src.stockage_observations import enregistrer_predictions
from src.database import SessionLocal
from src.db_models import Lot, ModelVersion, Observation


# =====================================================
# 2. APPLICATION FASTAPI
# =====================================================

app = FastAPI(
    title="AgriYield MLOps",
    description="Application de prédiction du rendement agricole",
    version="1.0.0"
)


# =====================================================
# 3. DOSSIERS ET COLONNES
# =====================================================

BASE_DIR = Path(__file__).resolve().parent.parent

templates = Jinja2Templates(
    directory=str(BASE_DIR / "frontend" / "templates")
)

app.mount(
    "/static",
    StaticFiles(
        directory=str(BASE_DIR / "frontend" / "static")
    ),
    name="static"
)

DOSSIER_EXPORTS = BASE_DIR / "exports"
DOSSIER_EXPORTS.mkdir(parents=True, exist_ok=True)

# Seulement les 8 caractéristiques du modèle.
COLONNES = list(COLONNES_ATTENDUES)

# Rendement réel facultatif.
COLONNE_YIELD = "Yield"


# =====================================================
# 4. PAGES HTML
# =====================================================

@app.get("/", response_class=HTMLResponse)
def bienvenue(request: Request):

    return templates.TemplateResponse(
        request=request,
        name="bienvenue.html"
    )


@app.get("/accueil", response_class=HTMLResponse)
def accueil(request: Request):

    return templates.TemplateResponse(
        request=request,
        name="accueil.html"
    )


@app.get("/prediction", response_class=HTMLResponse)
def page_prediction(request: Request):

    return templates.TemplateResponse(
        request=request,
        name="prediction.html",
        context={
            "crops": [],
            "seasons": [],
            "states": [],
            "version_modele": "V1"
        }
    )


# =====================================================
# 5. PREDICTION INDIVIDUELLE
# =====================================================

@app.post("/api/predictions")
def prediction_individuelle(
    observation: ObservationSchema
):
    """
    Prédiction à partir des 8 caractéristiques.

    Yield :
      - facultatif
      - jamais envoyé au modèle
      - stocké dans observations.rendement_reel
      - NULL si absent pour une nouvelle observation
    """

    # -----------------------------------------
    # 1. Récupérer Yield séparément
    # -----------------------------------------

    rendement_reel_saisi = (
        observation.obtenir_rendement_reel()
    )

    # -----------------------------------------
    # 2. Préparer uniquement les 8 features
    # -----------------------------------------

    df = pd.DataFrame([
        observation.donnees_pour_modele()
    ])

    # -----------------------------------------
    # 3. Effectuer la prédiction
    # -----------------------------------------

    donnees_valides, predictions, avertissements = (
        predire_rendement(df)
    )

    if donnees_valides.empty:

        raise HTTPException(
            status_code=422,
            detail={
                "message": "Observation refusée.",
                "avertissements": avertissements
            }
        )

    if len(donnees_valides) != 1 or len(predictions) != 1:

        raise HTTPException(
            status_code=500,
            detail=(
                "Résultat de prédiction individuelle "
                "incohérent."
            )
        )

    # -----------------------------------------
    # 4. Enregistrer dans MariaDB
    # -----------------------------------------

    with SessionLocal() as session:

        version = session.scalar(
            select(ModelVersion).where(
                ModelVersion.version == "V1"
            )
        )

        if version is None:

            raise HTTPException(
                status_code=500,
                detail="Modèle V1 introuvable dans MariaDB."
            )

        ids = enregistrer_predictions(
            session=session,
            donnees_valides=donnees_valides,
            predictions=predictions,
            model_version_id=version.id,
            lot_id=None,
            rendements_reels=[rendement_reel_saisi]
        )

        if not ids:

            raise HTTPException(
                status_code=500,
                detail=(
                    "Aucun identifiant d'observation retourné."
                )
            )

        observation_id = int(ids[0])

        # -------------------------------------
        # 5. Relire le rendement réel stocké
        # -------------------------------------

        # Important pour les doublons et conflits :
        # on retourne la valeur réellement conservée.

        observation_stockee = session.get(
            Observation,
            observation_id
        )

        if observation_stockee is None:

            raise HTTPException(
                status_code=500,
                detail=(
                    "Observation enregistrée introuvable."
                )
            )

        rendement_reel_stocke = (
            observation_stockee.rendement_reel
        )

    # -----------------------------------------
    # 6. Retourner le résultat
    # -----------------------------------------

    return {
        "statut": "succes",
        "observation_id": observation_id,
        "rendement_reel": (
            float(rendement_reel_stocke)
            if rendement_reel_stocke is not None
            else None
        ),
        "rendement_predit": float(predictions[0]),
        "version_modele": "V1"
    }


# =====================================================
# 6. FONCTIONS UTILITAIRES CSV
# =====================================================

def convertir_avertissements(avertissements):
    """
    Associe les motifs de refus aux indices
    des observations dans le DataFrame.
    """

    erreurs = {}

    for item in avertissements:

        if not isinstance(item, dict):
            continue

        try:
            indice = int(item["ligne"])

        except (KeyError, ValueError, TypeError):
            continue

        message = str(
            item.get(
                "message",
                "Observation invalide."
            )
        )

        if indice in erreurs:
            erreurs[indice] += " ; " + message

        else:
            erreurs[indice] = message

    return erreurs


def valider_rendement_reel(valeur):
    """
    Valide une valeur Yield issue du CSV.

    Retour :
        (rendement_reel, erreur)

    Valeurs autorisées :
        - None
        - cellule vide
        - null, none, nan, na
        - 0
        - nombre positif

    Valeurs refusées :
        - nombre négatif
        - texte non numérique
        - infini
    """

    if valeur is None:
        return None, None

    if pd.isna(valeur):
        return None, None

    if isinstance(valeur, str):

        valeur = valeur.strip()

        if valeur.lower() in {
            "",
            "null",
            "none",
            "nan",
            "na"
        }:
            return None, None

    if isinstance(valeur, bool):

        return None, (
            "Yield doit être un nombre."
        )

    try:
        rendement = float(valeur)

    except (TypeError, ValueError, OverflowError):

        return None, (
            f"Yield = {valeur} : "
            "le rendement réel doit être numérique."
        )

    if not math.isfinite(rendement):

        return None, (
            "Yield doit être un nombre fini."
        )

    if rendement < 0:

        return None, (
            f"Yield = {valeur} : "
            "le rendement réel doit être positif ou nul."
        )

    return rendement, None


# =====================================================
# 7. PREDICTION CSV AVEC YIELD FACULTATIF
# =====================================================

@app.post("/api/predictions/csv")
async def prediction_csv(
    file: UploadFile = File(...)
):

    # -----------------------------------------
    # 1. Vérifier le fichier
    # -----------------------------------------

    if (
        not file.filename
        or not file.filename.lower().endswith(".csv")
    ):

        raise HTTPException(
            status_code=400,
            detail="Veuillez importer un fichier CSV."
        )

    # -----------------------------------------
    # 2. Lire le CSV
    # -----------------------------------------

    try:

        contenu = await file.read()

        df = pd.read_csv(
            io.BytesIO(contenu)
        )

    except (
        UnicodeError,
        pd.errors.ParserError,
        pd.errors.EmptyDataError,
        ValueError
    ):

        raise HTTPException(
            status_code=400,
            detail=(
                "Le fichier CSV est illisible ou mal formé."
            )
        )

    finally:
        await file.close()

    if df.empty:

        raise HTTPException(
            status_code=422,
            detail=(
                "Le fichier CSV ne contient aucune observation."
            )
        )

    # -----------------------------------------
    # 3. Vérifier les colonnes
    # -----------------------------------------

    # Deux formats acceptés :
    # - 8 colonnes sans Yield
    # - 9 colonnes avec Yield

    avec_yield = COLONNE_YIELD in df.columns

    colonnes_attendues = set(COLONNES)

    if avec_yield:
        colonnes_attendues.add(COLONNE_YIELD)

    if (
        len(df.columns) != len(colonnes_attendues)
        or set(df.columns) != colonnes_attendues
    ):

        raise HTTPException(
            status_code=422,
            detail=(
                "Le CSV doit contenir les 8 caractéristiques "
                "agricoles, avec éventuellement une neuvième "
                "colonne nommée Yield."
            )
        )

    # Conserver les données originales pour l'export.
    df_original = df.copy()

    # Assurer la correspondance des indices.
    df = df.reset_index(drop=True)

    # -----------------------------------------
    # 4. Valider les rendements réels
    # -----------------------------------------

    rendements_reels = {}
    erreurs_yield = {}

    for position in range(len(df)):

        if avec_yield:
            valeur = df.iloc[position][COLONNE_YIELD]

        else:
            valeur = None

        rendement, erreur = valider_rendement_reel(
            valeur
        )

        rendements_reels[position] = rendement

        if erreur is not None:
            erreurs_yield[position] = erreur

    # -----------------------------------------
    # 5. Préparer les caractéristiques
    # -----------------------------------------

    # Le modèle reçoit uniquement les 8 features.
    # Yield est complètement exclu.

    df_features = df[COLONNES].copy()

    # -----------------------------------------
    # 6. Prédire
    # -----------------------------------------

    donnees_valides, predictions, avertissements = (
        predire_rendement(df_features)
    )

    if len(donnees_valides) != len(predictions):

        raise HTTPException(
            status_code=500,
            detail=(
                "Incohérence entre observations "
                "et prédictions."
            )
        )

    if not donnees_valides.index.is_unique:

        raise HTTPException(
            status_code=500,
            detail=(
                "Indices des observations valides "
                "non uniques."
            )
        )

    # -----------------------------------------
    # 7. Préparer les erreurs
    # -----------------------------------------

    erreurs = convertir_avertissements(
        avertissements
    )

    for position, message in erreurs_yield.items():

        if position in erreurs:
            erreurs[position] += " ; " + message

        else:
            erreurs[position] = message

    # -----------------------------------------
    # 8. Exclure les Yield invalides
    # -----------------------------------------

    indices_valides = [
        indice
        for indice in donnees_valides.index
        if int(indice) not in erreurs_yield
    ]

    donnees_a_stocker = donnees_valides.loc[
        indices_valides
    ].copy()

    # Associer chaque prédiction à son indice.
    predictions_par_indice = {
        int(indice): float(rendement)
        for indice, rendement in zip(
            donnees_valides.index,
            predictions
        )
    }

    predictions_a_stocker = [
        predictions_par_indice[int(indice)]
        for indice in indices_valides
    ]

    reels_a_stocker = [
        rendements_reels.get(int(indice))
        for indice in indices_valides
    ]

    # -----------------------------------------
    # 9. Préparer les résultats
    # -----------------------------------------

    indices_acceptes = {
        int(indice)
        for indice in indices_valides
    }

    resultats = []

    for position in range(len(df)):

        if position in indices_acceptes:

            resultats.append({
                "ligne": position + 2,
                "statut": "acceptee",
                "rendement_reel": rendements_reels.get(
                    position
                ),
                "rendement_predit": (
                    predictions_par_indice[position]
                ),
                "motif": ""
            })

        else:

            resultats.append({
                "ligne": position + 2,
                "statut": "refusee",
                "rendement_reel": rendements_reels.get(
                    position
                ),
                "rendement_predit": None,
                "motif": erreurs.get(
                    position,
                    "Observation invalide."
                )
            })

    nb_acceptees = len(indices_valides)
    nb_refusees = len(df) - nb_acceptees

    # -----------------------------------------
    # 10. Préparer les statistiques
    # -----------------------------------------

    lot_id = None

    nb_enregistrees = 0
    nb_doublons = 0
    nb_mises_a_jour = 0
    nb_conflits = 0

    chemin_temporaire = None
    chemin_export = None

    # -----------------------------------------
    # 11. Enregistrer le lot dans MariaDB
    # -----------------------------------------

    with SessionLocal() as session:

        try:

            version = session.scalar(
                select(ModelVersion).where(
                    ModelVersion.version == "V1"
                )
            )

            if version is None:

                raise HTTPException(
                    status_code=500,
                    detail=(
                        "Modèle V1 introuvable dans MariaDB."
                    )
                )

            # Créer le lot même si toutes
            # les observations sont refusées.

            lot = Lot(
                nom_lot=Path(file.filename).name,
                source="production",
                nombre_lignes=len(df)
            )

            session.add(lot)
            session.flush()

            lot_id = lot.id

            # ---------------------------------
            # 12. Stocker les lignes valides
            # ---------------------------------

            if nb_acceptees > 0:

                details = enregistrer_predictions(
                    session=session,
                    donnees_valides=donnees_a_stocker,
                    predictions=predictions_a_stocker,
                    model_version_id=version.id,
                    lot_id=lot_id,
                    commit=False,
                    retourner_details=True,
                    rendements_reels=reels_a_stocker
                )

                nb_enregistrees = details.get(
                    "nb_enregistrees",
                    0
                )

                nb_doublons = details.get(
                    "nb_doublons",
                    0
                )

                nb_mises_a_jour = details.get(
                    "nb_mises_a_jour",
                    0
                )

                nb_conflits = details.get(
                    "nb_conflits",
                    0
                )

                # ---------------------------------
                # 13. Actualiser les statuts
                # ---------------------------------

                for indice, statut in zip(
                    indices_valides,
                    details["statuts"]
                ):

                    position = int(indice)

                    if statut == "doublon":

                        resultats[position]["statut"] = (
                            "doublon"
                        )

                        resultats[position]["motif"] = (
                            "Observation déjà présente dans "
                            "MariaDB. Aucune nouvelle "
                            "observation créée."
                        )

                    elif statut == "mise_a_jour":

                        resultats[position]["statut"] = (
                            "mise_a_jour"
                        )

                        resultats[position]["motif"] = (
                            "Observation existante : "
                            "rendement réel ajouté dans MariaDB."
                        )

                    elif statut == "conflit":

                        resultats[position]["statut"] = (
                            "conflit"
                        )

                        resultats[position]["motif"] = (
                            "Un rendement réel différent "
                            "existe déjà dans MariaDB. "
                            "La valeur existante a été conservée."
                        )

                # ---------------------------------
                # 14. Relire les rendements réels
                # ---------------------------------

                # Garantir que les résultats affichés
                # correspondent aux valeurs réellement
                # conservées dans MariaDB.

                ids_observations = details.get("ids")

                if ids_observations is not None:

                    for indice, observation_id in zip(
                        indices_valides,
                        ids_observations
                    ):

                        position = int(indice)

                        observation_stockee = session.get(
                            Observation,
                            int(observation_id)
                        )

                        if observation_stockee is not None:

                            valeur_stockee = (
                                observation_stockee.rendement_reel
                            )

                            resultats[position][
                                "rendement_reel"
                            ] = (
                                float(valeur_stockee)
                                if valeur_stockee is not None
                                else None
                            )

            # ---------------------------------
            # 15. Préparer le fichier CSV export
            # ---------------------------------

            df_export = df_original.copy()

            df_export.insert(
                0,
                "Ligne_CSV",
                [i + 2 for i in range(len(df))]
            )

            # Éviter une duplication de Yield.
            if COLONNE_YIELD in df_export.columns:

                df_export = df_export.drop(
                    columns=[COLONNE_YIELD]
                )

            df_export["Rendement_reel_t_ha"] = [
                item["rendement_reel"]
                for item in resultats
            ]

            df_export["Rendement_predit_t_ha"] = [
                item["rendement_predit"]
                for item in resultats
            ]

            df_export["Statut"] = [
                item["statut"]
                for item in resultats
            ]

            df_export["Motif"] = [
                item["motif"]
                for item in resultats
            ]

            # ---------------------------------
            # 16. Préparer le chemin d'export
            # ---------------------------------

            chemin_export = (
                DOSSIER_EXPORTS /
                f"lot_{lot_id}.csv"
            )

            fd, chemin_temporaire = tempfile.mkstemp(
                prefix=f"lot_{lot_id}_",
                suffix=".tmp",
                dir=DOSSIER_EXPORTS
            )

            os.close(fd)

            # ---------------------------------
            # 17. Écrire le CSV et valider SQL
            # ---------------------------------

            try:

                df_export.to_csv(
                    chemin_temporaire,
                    index=False,
                    encoding="utf-8-sig"
                )

                session.commit()

            except Exception:

                session.rollback()

                Path(chemin_temporaire).unlink(
                    missing_ok=True
                )

                raise

        except Exception:

            session.rollback()

            if chemin_temporaire is not None:
                Path(chemin_temporaire).unlink(
                    missing_ok=True
                )

            raise

    # -----------------------------------------
    # 18. Publier le fichier CSV
    # -----------------------------------------

    try:

        os.replace(
            chemin_temporaire,
            chemin_export
        )

    except OSError:

        Path(chemin_temporaire).unlink(
            missing_ok=True
        )

        raise HTTPException(
            status_code=500,
            detail=(
                "Lot enregistré dans MariaDB, "
                "mais création de l'export impossible."
            )
        )

    # -----------------------------------------
    # 19. Retourner le bilan au frontend
    # -----------------------------------------

    return {
        "statut": "succes",
        "lot_id": lot_id,
        "version_modele": "V1",
        "total": len(df),
        "nb_acceptees": nb_acceptees,
        "nb_refusees": nb_refusees,
        "nb_enregistrees": nb_enregistrees,
        "nb_doublons": nb_doublons,
        "nb_mises_a_jour": nb_mises_a_jour,
        "nb_conflits": nb_conflits,
        "resultats": resultats,
        "url_export": f"/api/lots/{lot_id}/export"
    }


# =====================================================
# 8. EXPORT DES RESULTATS CSV
# =====================================================

@app.get("/api/lots/{lot_id}/export")
def exporter_resultats(lot_id: int):

    chemin = (
        DOSSIER_EXPORTS /
        f"lot_{lot_id}.csv"
    )

    if not chemin.is_file():

        raise HTTPException(
            status_code=404,
            detail="Résultats CSV introuvables."
        )

    return FileResponse(
        path=chemin,
        media_type="text/csv",
        filename=f"resultats_lot_{lot_id}.csv"
    )


# =====================================================
# 9. VERIFICATION DU SERVEUR
# =====================================================

@app.get("/api/health")
def verifier_serveur():

    return {
        "statut": "ok",
        "application": "AgriYield MLOps"
    }


# =====================================================
# 10. PAGE HISTORIQUE
# =====================================================

@app.get("/historique", response_class=HTMLResponse)
def page_historique(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="historique.html"
    )


# =====================================================
# 11. SERIALISATION DES OBJETS SQLALCHEMY
# =====================================================

def serialiser_historique(objet):
    """Convertir les colonnes SQLAlchemy en dictionnaire JSON."""
    resultat = {}
    for colonne in inspect(objet).mapper.column_attrs:
        valeur = getattr(objet, colonne.key)
        if isinstance(valeur, (datetime, date)):
            valeur = valeur.isoformat()
        elif hasattr(valeur, "as_tuple"):
            valeur = float(valeur)
        resultat[colonne.key] = valeur
    return resultat


# =====================================================
# 12. HISTORIQUE DES PREDICTIONS ET FILTRES
# =====================================================

@app.get("/api/observations")
def lire_historique(
    date_debut: Optional[date] = None,
    date_fin: Optional[date] = None,
    model_version_id: Optional[int] = None
):
    if date_debut and date_fin and date_debut > date_fin:
        raise HTTPException(
            status_code=422,
            detail="La date de début dépasse la date de fin."
        )

    with SessionLocal() as session:
        requete = (
            select(Prediction, Observation, ModelVersion)
            .join(Observation, Prediction.observation_id == Observation.id)
            .join(ModelVersion, Prediction.model_version_id == ModelVersion.id)
        )

        # Filtrage sur la date d'enregistrement de l'observation.
        # Vérifier le nom de cette colonne dans src/db_models.py.
        colonne_date = Observation.date_observation

        if date_debut is not None:
            requete = requete.where(func.date(colonne_date) >= date_debut)
        if date_fin is not None:
            requete = requete.where(func.date(colonne_date) <= date_fin)
        if model_version_id is not None:
            requete = requete.where(
                Prediction.model_version_id == model_version_id
            )

        lignes = session.execute(
            requete.order_by(Prediction.id.desc()).limit(500)
        ).all()

        versions = session.scalars(
            select(ModelVersion).order_by(ModelVersion.id)
        ).all()

        nb_observations = session.scalar(
            select(func.count(Observation.id))
        ) or 0
        nb_predictions = session.scalar(
            select(func.count(Prediction.id))
        ) or 0
        nb_reels = session.scalar(
            select(func.count(Observation.id)).where(
                Observation.rendement_reel.is_not(None)
            )
        ) or 0

        return {
            "historique": [
                {
                    "prediction": serialiser_historique(prediction),
                    "observation": serialiser_historique(observation),
                    "modele": serialiser_historique(modele)
                }
                for prediction, observation, modele in lignes
            ],
            "versions": [serialiser_historique(v) for v in versions],
            "statistiques": {
                "observations": nb_observations,
                "predictions": nb_predictions,
                "rendements_reels": nb_reels
            }
        }


# =====================================================
# 13. DETAILS D'UNE OBSERVATION
# =====================================================

@app.get("/api/observations/{observation_id}")
def obtenir_detail_observation(observation_id: int):
    with SessionLocal() as session:
        observation = session.get(Observation, observation_id)
        if observation is None:
            raise HTTPException(
                status_code=404,
                detail="Observation introuvable."
            )

        predictions = session.scalars(
            select(Prediction)
            .where(Prediction.observation_id == observation_id)
            .order_by(Prediction.id.desc())
        ).all()

        return {
            "observation": serialiser_historique(observation),
            "predictions": [
                serialiser_historique(prediction)
                for prediction in predictions
            ]
        }


# =====================================================
# 14. AJOUTER UN RENDEMENT REEL MANQUANT
# =====================================================

@app.patch("/api/observations/{observation_id}/rendement-reel")
def mettre_a_jour_rendement_reel(
    observation_id: int,
    donnees: dict = Body(...)
):
    valeur = donnees.get("rendement_reel")

    if (
        valeur is None
        or isinstance(valeur, bool)
        or (isinstance(valeur, str) and not valeur.strip())
    ):
        raise HTTPException(
            status_code=422,
            detail="Le rendement réel est obligatoire."
        )

    try:
        rendement = float(valeur)
    except (TypeError, ValueError, OverflowError):
        raise HTTPException(
            status_code=422,
            detail="Le rendement réel doit être numérique."
        )

    if not math.isfinite(rendement) or rendement < 0:
        raise HTTPException(
            status_code=422,
            detail="Le rendement réel doit être positif ou nul."
        )

    with SessionLocal() as session:
        try:
            observation = session.get(
                Observation, observation_id, with_for_update=True
            )
            if observation is None:
                raise HTTPException(
                    status_code=404,
                    detail="Observation introuvable."
                )
            if observation.rendement_reel is not None:
                raise HTTPException(
                    status_code=409,
                    detail="Cette observation possède déjà un rendement réel."
                )

            observation.rendement_reel = rendement
            session.commit()

            return {
                "statut": "succes",
                "message": "Rendement réel enregistré.",
                "observation_id": observation_id,
                "rendement_reel": rendement
            }
        except Exception:
            session.rollback()
            raise
