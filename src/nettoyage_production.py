
# ==========================================
# AGRIYIELD MLOPS
# VALIDATION ET NETTOYAGE PRODUCTION
# Fichier : src/nettoyage_production.py
# ==========================================

import pandas as pd
import numpy as np

from numbers import Real

from .nettoyage_dataset import (
    FEATURES,
    CATEGORICAL,
    NUMERIC,
    nettoyer_features
)


# ==========================================
# 1. CONFIGURATION
# ==========================================

MAX_MANQUANTS = 3

VALEURS_MANQUANTES = {
    "",
    "null",
    "none",
    "nan",
    "na"
}

FORMATS_ATTENDUS = {
    "Crop": "Texte non vide, ex. Rice",
    "Season": "Texte non vide, ex. Kharif",
    "State": "Texte non vide, ex. Assam",
    "Crop_Year": "Année entière entre 1900 et 2100",
    "Area": "Nombre positif ou nul, ex. 150",
    "Annual_Rainfall": "Nombre positif ou nul, ex. 1200",
    "Fertilizer": "Nombre positif ou nul, ex. 200",
    "Pesticide": "Nombre positif ou nul, ex. 15"
}


# ==========================================
# 2. DETECTER LES VALEURS MANQUANTES
# ==========================================

def est_manquant(valeur):
    """
    Détecter une valeur manquante.

    Valeurs considérées comme manquantes :
    - None
    - NaN
    - pd.NA
    - chaîne vide
    - null, none, nan, na
    """

    if valeur is None:
        return True

    if isinstance(valeur, str):

        return (
            valeur.strip().lower()
            in VALEURS_MANQUANTES
        )

    if isinstance(
        valeur,
        (list, dict, tuple, set)
    ):
        return False

    try:

        resultat = pd.isna(valeur)

        if isinstance(
            resultat,
            (bool, np.bool_)
        ):
            return bool(resultat)

    except (TypeError, ValueError):
        pass

    return False


# ==========================================
# 3. FORMATER UNE VALEUR POUR LES MESSAGES
# ==========================================

def formater_valeur(valeur):
    """
    Convertir une valeur en texte lisible
    pour afficher les messages d'erreur.
    """

    if isinstance(valeur, str):
        return valeur.strip()

    if isinstance(valeur, (list, dict, tuple, set)):
        return str(valeur)

    if est_manquant(valeur):
        return "NULL"

    return str(valeur)


# ==========================================
# 4. VALIDATION DETAILLEE D'UN CHAMP
# ==========================================

def valider_champ_detaille(champ, valeur):
    """
    Vérifier un champ et retourner :

    - statut : valide, manquant ou invalide
    - message : raison précise si invalide

    Les valeurs manquantes sont traitées
    séparément des valeurs incorrectes.
    """

    # --------------------------------------
    # 1. Valeur manquante
    # --------------------------------------

    if est_manquant(valeur):

        return {
            "statut": "manquant",
            "message": None
        }

    # --------------------------------------
    # 2. Variables catégorielles
    # --------------------------------------

    if champ in CATEGORICAL:

        if not isinstance(valeur, str):

            return {
                "statut": "invalide",
                "message": (
                    f"{champ} = {formater_valeur(valeur)} : "
                    "une valeur textuelle est attendue."
                )
            }

        if valeur.strip() == "":

            return {
                "statut": "manquant",
                "message": None
            }

        return {
            "statut": "valide",
            "message": None
        }

    # --------------------------------------
    # 3. Vérifier le type numérique
    # --------------------------------------

    if champ not in NUMERIC:

        return {
            "statut": "invalide",
            "message": (
                f"{champ} : caractéristique inconnue."
            )
        }

    if isinstance(
        valeur,
        (bool, np.bool_)
    ):

        return {
            "statut": "invalide",
            "message": (
                f"{champ} = {valeur} : "
                "une valeur numérique est attendue."
            )
        }

    if not isinstance(
        valeur,
        (str, Real, np.number)
    ):

        return {
            "statut": "invalide",
            "message": (
                f"{champ} = {formater_valeur(valeur)} : "
                "une valeur numérique est attendue."
            )
        }

    # --------------------------------------
    # 4. Conversion numérique
    # --------------------------------------

    try:

        nombre = float(valeur)

    except (ValueError, TypeError, OverflowError):

        return {
            "statut": "invalide",
            "message": (
                f"{champ} = {formater_valeur(valeur)} : "
                "une valeur numérique est attendue."
            )
        }

    # --------------------------------------
    # 5. Vérifier les valeurs infinies
    # --------------------------------------

    if not np.isfinite(nombre):

        return {
            "statut": "invalide",
            "message": (
                f"{champ} = {formater_valeur(valeur)} : "
                "la valeur doit être un nombre fini."
            )
        }

    # --------------------------------------
    # 6. Vérifier Crop_Year
    # --------------------------------------

    if champ == "Crop_Year":

        if (
            not nombre.is_integer()
            or not (1900 <= nombre <= 2100)
        ):

            return {
                "statut": "invalide",
                "message": (
                    f"Crop_Year = {formater_valeur(valeur)} : "
                    "l'année doit être un entier "
                    "entre 1900 et 2100."
                )
            }

        return {
            "statut": "valide",
            "message": None
        }

    # --------------------------------------
    # 7. Vérifier les valeurs négatives
    # --------------------------------------

    if nombre < 0:

        return {
            "statut": "invalide",
            "message": (
                f"{champ} = {formater_valeur(valeur)} : "
                f"{champ} doit être positif ou nul."
            )
        }

    return {
        "statut": "valide",
        "message": None
    }


# ==========================================
# 5. VALIDATION SIMPLE
# ==========================================

def valider_champ(champ, valeur):
    """
    Conserver la compatibilité avec les
    autres fichiers du projet.

    Retourne uniquement :
    - valide
    - manquant
    - invalide
    """

    resultat = valider_champ_detaille(
        champ,
        valeur
    )

    return resultat["statut"]


# ==========================================
# 6. NETTOYAGE DES DONNEES DE PRODUCTION
# ==========================================

def nettoyer_production(df):
    """
    Valider et nettoyer les observations
    de production.

    Une observation est acceptée si :
    - Aucun champ renseigné n'est invalide.
    - Maximum 3 champs sont manquants.

    Chaque observation est vérifiée
    individuellement.

    Les observations invalides ne sont
    pas retournées pour la prédiction.

    Retour :
        donnees_valides, avertissements
    """

    donnees_brutes = df.copy()

    # --------------------------------------
    # 1. Compléter les colonnes absentes
    # --------------------------------------

    for champ in FEATURES:

        if champ not in donnees_brutes.columns:

            donnees_brutes[champ] = pd.NA

    # --------------------------------------
    # 2. Préparer les résultats
    # --------------------------------------

    lignes_acceptees = []
    avertissements = []

    # --------------------------------------
    # 3. Parcourir les observations
    # --------------------------------------

    for position in range(len(donnees_brutes)):

        ligne = donnees_brutes.iloc[position]

        champs_manquants = []
        champs_invalides = []
        messages_erreurs = []

        # ----------------------------------
        # 4. Vérifier chaque champ
        # ----------------------------------

        for champ in FEATURES:

            resultat = valider_champ_detaille(
                champ,
                ligne[champ]
            )

            statut = resultat["statut"]

            if statut == "manquant":

                champs_manquants.append(champ)

            elif statut == "invalide":

                champs_invalides.append(champ)

                if resultat["message"]:

                    messages_erreurs.append(
                        resultat["message"]
                    )

        # ----------------------------------
        # 5. Compter les valeurs manquantes
        # ----------------------------------

        nombre_manquants = len(
            champs_manquants
        )

        # ----------------------------------
        # 6. Accepter une observation valide
        # ----------------------------------

        if (
            len(champs_invalides) == 0
            and nombre_manquants <= MAX_MANQUANTS
        ):

            lignes_acceptees.append(
                position
            )

            continue

        # ----------------------------------
        # 7. Signaler trop de valeurs manquantes
        # ----------------------------------

        if nombre_manquants > MAX_MANQUANTS:

            messages_erreurs.append(
                f"{nombre_manquants} champs sont manquants "
                f"({', '.join(champs_manquants)}). "
                f"Maximum autorisé : {MAX_MANQUANTS}."
            )

        # ----------------------------------
        # 8. Formats attendus
        # ----------------------------------

        formats_a_corriger = {
            champ: FORMATS_ATTENDUS[champ]
            for champ in champs_invalides
        }

        if nombre_manquants > MAX_MANQUANTS:

            for champ in champs_manquants:

                formats_a_corriger[champ] = (
                    FORMATS_ATTENDUS[champ]
                )

        # ----------------------------------
        # 9. Enregistrer les avertissements
        # ----------------------------------

        avertissements.append({
            "ligne": position,
            "nombre_manquants": nombre_manquants,
            "champs_manquants": champs_manquants,
            "champs_invalides": champs_invalides,
            "message": " ".join(messages_erreurs),
            "formats_attendus": formats_a_corriger
        })

    # --------------------------------------
    # 10. Nettoyer uniquement les lignes valides
    # --------------------------------------

    donnees_valides_brutes = (
        donnees_brutes.iloc[
            lignes_acceptees
        ].copy()
    )

    # Préserver les indices d'origine
    # pour associer chaque prédiction
    # à la bonne ligne du fichier CSV.

    if donnees_valides_brutes.empty:

        donnees_valides = (
            donnees_valides_brutes[FEATURES].copy()
        )

    else:

        donnees_valides = nettoyer_features(
            donnees_valides_brutes
        )

    return donnees_valides, avertissements
