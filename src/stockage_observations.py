
# ==========================================
# AGRIYIELD MLOPS
# STOCKAGE DES OBSERVATIONS ET PREDICTIONS
# Fichier : src/stockage_observations.py
# ==========================================

import math

import numpy as np
import pandas as pd

from sqlalchemy import select, and_
from sqlalchemy.exc import IntegrityError

from .db_models import Observation, Prediction


# =====================================================
# 1. COLONNES A COMPARER
# =====================================================

COLONNES = [
    "Crop",
    "Season",
    "State",
    "Crop_Year",
    "Area",
    "Annual_Rainfall",
    "Fertilizer",
    "Pesticide",
]

COLONNES_NUMERIQUES = [
    "Crop_Year",
    "Area",
    "Annual_Rainfall",
    "Fertilizer",
    "Pesticide",
]

# Tolérance pour les conversions pandas / MariaDB
TOLERANCE_ABSOLUE = 1e-7


# =====================================================
# 2. CONVERSION DES VALEURS
# =====================================================

def convertir_valeur(valeur):
    """
    Convertir les valeurs pandas / numpy
    en valeurs Python.

    Les valeurs manquantes deviennent None
    pour être enregistrées comme NULL dans MariaDB.
    """

    if valeur is None:
        return None

    try:
        manquante = pd.isna(valeur)

        if isinstance(manquante, (bool, np.bool_)) and manquante:
            return None

    except (TypeError, ValueError):
        pass

    if hasattr(valeur, "item"):
        valeur = valeur.item()

    return valeur


# =====================================================
# 3. COMPARAISON DES VALEURS
# =====================================================

def valeurs_equivalentes(colonne, gauche, droite):
    """
    Comparer deux valeurs.

    Pour les valeurs numériques, utiliser une tolérance
    afin d'éviter les différences liées aux flottants.
    """

    gauche = convertir_valeur(gauche)
    droite = convertir_valeur(droite)

    if gauche is None or droite is None:
        return gauche is None and droite is None

    if colonne in COLONNES_NUMERIQUES:

        try:
            return math.isclose(
                float(gauche),
                float(droite),
                rel_tol=0.0,
                abs_tol=TOLERANCE_ABSOLUE,
            )

        except (TypeError, ValueError, OverflowError):
            return False

    return gauche == droite


# =====================================================
# 4. RECHERCHER UNE OBSERVATION IDENTIQUE
# =====================================================

def rechercher_observation_existante(session, valeurs):
    """
    Rechercher une observation à partir
    de ses huit caractéristiques.

    Le rendement réel, la date et le lot
    ne participent pas à la comparaison.

    Les valeurs numériques sont comparées
    avec une petite tolérance.
    """

    conditions = []

    # Filtrer d'abord les catégories
    for colonne in ["Crop", "Season", "State"]:

        champ = getattr(Observation, colonne)
        valeur = convertir_valeur(valeurs[colonne])

        if valeur is None:
            conditions.append(champ.is_(None))
        else:
            conditions.append(champ == valeur)

    # Filtrer les valeurs numériques manquantes
    for colonne in COLONNES_NUMERIQUES:

        if convertir_valeur(valeurs[colonne]) is None:

            champ = getattr(Observation, colonne)
            conditions.append(champ.is_(None))

    candidats = session.scalars(
        select(Observation)
        .where(and_(*conditions))
        .order_by(Observation.id.asc())
    )

    # Vérifier les huit caractéristiques
    for observation in candidats:

        identique = all(
            valeurs_equivalentes(
                colonne,
                getattr(observation, colonne),
                valeurs[colonne],
            )
            for colonne in COLONNES
        )

        if identique:
            return observation

    return None


# =====================================================
# 5. RECHERCHER UNE PREDICTION EXISTANTE
# =====================================================

def rechercher_prediction_existante(
    session,
    observation_id,
    model_version_id,
):
    """
    Vérifier si une prédiction existe déjà
    pour cette observation et cette version du modèle.
    """

    return session.scalar(
        select(Prediction)
        .where(
            Prediction.observation_id == observation_id,
            Prediction.model_version_id == model_version_id,
        )
        .order_by(Prediction.id.asc())
        .limit(1)
    )


# =====================================================
# 6. CREER OU RETROUVER UNE OBSERVATION
# =====================================================

def creer_ou_retrouver_observation(
    session,
    valeurs,
    rendement_reel,
    lot_id,
):
    """
    Créer une observation uniquement si elle
    n'existe pas déjà.

    Si MariaDB détecte une empreinte dupliquée,
    annuler uniquement la tentative d'insertion
    grâce à une transaction imbriquée.

    Le reste du traitement CSV reste intact.
    """

    # Rechercher avant d'insérer
    observation = rechercher_observation_existante(
        session,
        valeurs,
    )

    if observation is not None:
        return observation, False

    # Essayer de créer une nouvelle observation
    try:

        with session.begin_nested():

            observation = Observation(
                lot_id=lot_id,
                rendement_reel=rendement_reel,
                **valeurs,
            )

            session.add(observation)
            session.flush()

        return observation, True

    except IntegrityError as erreur:

        message = (
            str(erreur.orig)
            if erreur.orig is not None
            else str(erreur)
        )

        # Ne traiter ici que la contrainte
        # d'unicité des observations
        if (
            "1062" not in message
            or "uq_observations_empreinte" not in message
        ):
            raise

        print(
            "[MariaDB] Empreinte déjà présente. "
            "Recherche de l'observation existante."
        )

        # La transaction imbriquée a été annulée.
        # La transaction principale reste utilisable.
        session.expire_all()

        observation = rechercher_observation_existante(
            session,
            valeurs,
        )

        if observation is None:

            raise ValueError(
                "MariaDB a détecté une empreinte "
                "d'observation déjà présente, mais aucune "
                "observation équivalente n'a été retrouvée. "
                "Vérifier la règle de calcul de l'empreinte "
                "et la précision des colonnes numériques "
                "dans src/db_models.py et MariaDB."
            ) from erreur

        return observation, False


# =====================================================
# 7. ENREGISTREMENT SANS DOUBLONS
# =====================================================

def enregistrer_predictions(
    session,
    donnees_valides,
    predictions,
    model_version_id,
    lot_id=None,
    commit=True,
    retourner_details=False,
    rendements_reels=None,
):
    """
    Enregistrer les observations et les prédictions.

    REGLES :

    1. Si les huit caractéristiques sont nouvelles :
       - créer une observation ;
       - enregistrer le rendement réel si disponible ;
       - enregistrer la prédiction.

    2. Si les huit caractéristiques existent déjà :
       - réutiliser l'observation existante ;
       - ne pas créer de doublon.

    3. Si Yield est fourni et rendement_reel est NULL :
       - compléter rendement_reel.

    4. Si un rendement réel différent existe déjà :
       - signaler un conflit ;
       - conserver la valeur existante.

    5. Ne pas créer deux prédictions pour une même
       observation et une même version du modèle.

    6. Yield n'est jamais envoyé au modèle V1.

    commit=True :
       valider automatiquement la transaction.

    commit=False :
       laisser api/main.py valider la transaction.

    retourner_details=True :
       retourner les identifiants et les statuts.
    """

    # -------------------------------------------------
    # 1. Vérifier les dimensions
    # -------------------------------------------------

    if len(donnees_valides) != len(predictions):

        raise ValueError(
            "Le nombre d'observations et de prédictions "
            "doit être identique."
        )

    if rendements_reels is None:

        rendements_reels = [
            None
        ] * len(donnees_valides)

    if len(rendements_reels) != len(donnees_valides):

        raise ValueError(
            "Le nombre de rendements réels doit être "
            "identique au nombre d'observations."
        )

    identifiants = []
    statuts = []

    # -------------------------------------------------
    # 2. Parcourir les observations
    # -------------------------------------------------

    try:

        for (_, ligne), rendement, reel in zip(
            donnees_valides.iterrows(),
            predictions,
            rendements_reels,
        ):

            # Les huit caractéristiques uniquement
            valeurs = {
                colonne: convertir_valeur(ligne[colonne])
                for colonne in COLONNES
            }

            # Le rendement réel est traité séparément
            rendement_reel = convertir_valeur(reel)

            if rendement_reel is not None:

                rendement_reel = float(rendement_reel)

                if (
                    not math.isfinite(rendement_reel)
                    or rendement_reel < 0
                ):

                    raise ValueError(
                        "Le rendement réel doit être "
                        "un nombre positif ou nul."
                    )

            rendement_predit = float(rendement)

            if not math.isfinite(rendement_predit):

                raise ValueError(
                    "La prédiction doit être un nombre fini."
                )

            # -----------------------------------------
            # 3. Créer ou retrouver l'observation
            # -----------------------------------------

            observation, nouvelle_observation = (
                creer_ou_retrouver_observation(
                    session,
                    valeurs,
                    rendement_reel,
                    lot_id,
                )
            )

            # -----------------------------------------
            # 4. Nouvelle observation
            # -----------------------------------------

            if nouvelle_observation:

                statut = "enregistree"

                print(
                    "[MariaDB] Nouvelle observation :",
                    observation.id,
                )

            # -----------------------------------------
            # 5. Compléter le rendement réel
            # -----------------------------------------

            elif (
                rendement_reel is not None
                and observation.rendement_reel is None
            ):

                observation.rendement_reel = rendement_reel

                statut = "mise_a_jour"

                print(
                    "[MariaDB] Rendement réel ajouté :",
                    observation.id,
                )

            # -----------------------------------------
            # 6. Détecter un conflit de rendement réel
            # -----------------------------------------

            elif (
                rendement_reel is not None
                and observation.rendement_reel is not None
                and not math.isclose(
                    float(observation.rendement_reel),
                    rendement_reel,
                    rel_tol=0.0,
                    abs_tol=1e-9,
                )
            ):

                statut = "conflit"

                print(
                    "[MariaDB] Conflit rendement réel :",
                    observation.id,
                )

                # Ne pas modifier la valeur existante

            # -----------------------------------------
            # 7. Observation déjà présente
            # -----------------------------------------

            else:

                statut = "doublon"

                print(
                    "[MariaDB] Observation déjà présente :",
                    observation.id,
                )

            # -----------------------------------------
            # 8. Vérifier la prédiction
            # -----------------------------------------

            prediction_existante = (
                rechercher_prediction_existante(
                    session,
                    observation.id,
                    model_version_id,
                )
            )

            # -----------------------------------------
            # 9. Enregistrer la prédiction si nécessaire
            # -----------------------------------------

            if prediction_existante is None:

                prediction = Prediction(
                    observation_id=observation.id,
                    model_version_id=model_version_id,
                    rendement_predit=rendement_predit,
                )

                session.add(prediction)

                print(
                    "[MariaDB] Prédiction enregistrée :",
                    observation.id,
                )

            else:

                print(
                    "[MariaDB] Prédiction déjà existante :",
                    observation.id,
                )

            # -----------------------------------------
            # 10. Conserver les résultats
            # -----------------------------------------

            identifiants.append(observation.id)
            statuts.append(statut)

        # ---------------------------------------------
        # 11. Valider la transaction
        # ---------------------------------------------

        if commit:
            session.commit()

        # ---------------------------------------------
        # 12. Retourner les résultats
        # ---------------------------------------------

        if retourner_details:

            return {
                "identifiants": identifiants,
                "statuts": statuts,
                "nb_enregistrees": statuts.count(
                    "enregistree"
                ),
                "nb_doublons": statuts.count(
                    "doublon"
                ),
                "nb_mises_a_jour": statuts.count(
                    "mise_a_jour"
                ),
                "nb_conflits": statuts.count(
                    "conflit"
                ),
            }

        return identifiants

    # -------------------------------------------------
    # 13. Annuler en cas d'erreur
    # -------------------------------------------------

    except Exception:

        session.rollback()
        raise
