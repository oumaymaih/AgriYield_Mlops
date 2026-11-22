
# ==========================================
# AGRIYIELD MLOPS
# NETTOYAGE DES DONNEES D'ENTRAINEMENT
# Fichier : src/nettoyage_dataset.py
# ==========================================

import pandas as pd
import numpy as np


# ==========================================
# 1. CONFIGURATION
# ==========================================

TARGET = "Yield"

# Variables numériques
NUMERIC = [
    "Crop_Year",
    "Area",
    "Annual_Rainfall",
    "Fertilizer",
    "Pesticide"
]

# Variables catégorielles
CATEGORICAL = [
    "Crop",
    "Season",
    "State"
]

# Les 8 caractéristiques utilisées par le modèle
FEATURES = CATEGORICAL + NUMERIC

# Colonnes nécessaires pour l'entraînement
REQUIRED = FEATURES + [TARGET]

# Valeurs textuelles considérées comme manquantes
VALEURS_MANQUANTES = {
    "",
    "null",
    "none",
    "nan",
    "na"
}


# ==========================================
# 2. NETTOYAGE COMMUN TRAIN / PRODUCTION
# ==========================================

def nettoyer_features(df):
    """
    Nettoyage commun des caractéristiques.

    Règles :
    - 8 caractéristiques attendues.
    - Les colonnes absentes sont créées avec NA.
    - Les catégories sont normalisées.
    - Les valeurs textuelles manquantes deviennent NA.
    - Les variables numériques doivent être finies.
    - Les valeurs numériques négatives sont interdites.
    - Crop_Year doit être entier entre 1900 et 2100.
    - Aucune observation n'est supprimée ici.
    - Production et Yield ne sont pas utilisées.
    """

    d = df.copy()

    # --------------------------------------
    # 1. Compléter les colonnes absentes
    # --------------------------------------

    for colonne in FEATURES:

        if colonne not in d.columns:
            d[colonne] = pd.NA

    # --------------------------------------
    # 2. Nettoyer les catégories
    # --------------------------------------

    for colonne in CATEGORICAL:

        # Convertir en texte pandas
        valeurs = d[colonne].astype("string")

        # Supprimer les espaces
        valeurs = valeurs.str.strip()

        # Identifier les marqueurs de valeurs manquantes
        masque_manquant = (
            valeurs.str.lower().isin(VALEURS_MANQUANTES)
        ).fillna(False)

        valeurs = valeurs.mask(
            masque_manquant,
            pd.NA
        )

        # Normaliser la casse
        valeurs = valeurs.str.title()

        d[colonne] = valeurs

    # --------------------------------------
    # 3. Nettoyer les variables numériques
    # --------------------------------------

    for colonne in NUMERIC:

        valeurs = d[colonne].copy()

        # Supprimer les espaces uniquement
        # pour les valeurs de type texte
        valeurs = valeurs.map(
            lambda valeur: (
                valeur.strip()
                if isinstance(valeur, str)
                else valeur
            )
        )

        # Transformer les marqueurs textuels
        # de valeurs manquantes en NaN
        valeurs = valeurs.map(
            lambda valeur: (
                np.nan
                if isinstance(valeur, str)
                and valeur.lower() in VALEURS_MANQUANTES
                else valeur
            )
        )

        # Convertir les valeurs en nombres
        valeurs = pd.to_numeric(
            valeurs,
            errors="coerce"
        )

        # Remplacer les valeurs infinies par NaN
        valeurs = valeurs.replace(
            [np.inf, -np.inf],
            np.nan
        )

        d[colonne] = valeurs

    # --------------------------------------
    # 4. Interdire les valeurs négatives
    # --------------------------------------

    for colonne in [
        "Area",
        "Annual_Rainfall",
        "Fertilizer",
        "Pesticide"
    ]:

        d.loc[
            d[colonne] < 0,
            colonne
        ] = np.nan

    # --------------------------------------
    # 5. Vérifier l'année
    # --------------------------------------

    annee = d["Crop_Year"]

    masque_annee_invalide = (
        (annee < 1900) |
        (annee > 2100) |
        ((annee % 1) != 0)
    )

    d.loc[
        masque_annee_invalide,
        "Crop_Year"
    ] = np.nan

    # --------------------------------------
    # 6. Retourner les 8 caractéristiques
    # --------------------------------------

    return d[FEATURES].copy()


# ==========================================
# 3. NETTOYAGE DU DATASET HISTORIQUE
# ==========================================

def nettoyer_dataset(df):
    """
    Nettoyage des données historiques.

    Etapes :
    1. Vérifier la présence de Yield.
    2. Supprimer les doublons.
    3. Nettoyer les 8 caractéristiques.
    4. Nettoyer Yield.
    5. Supprimer les lignes dont Yield est invalide
       ou dont toutes les caractéristiques
       sont manquantes.

    La colonne Production est exclue.

    Retour :
        DataFrame nettoyé avec les 8
        caractéristiques et Yield.
    """

    d = df.copy()

    # --------------------------------------
    # 1. Vérifier la variable cible
    # --------------------------------------

    if TARGET not in d.columns:

        raise ValueError(
            "La colonne Yield est absente."
        )

    # --------------------------------------
    # 2. Supprimer les doublons
    # --------------------------------------

    d = d.drop_duplicates().copy()

    # --------------------------------------
    # 3. Nettoyer les caractéristiques
    # --------------------------------------

    x = nettoyer_features(d)

    # --------------------------------------
    # 4. Nettoyer la variable cible
    # --------------------------------------

    y = pd.to_numeric(
        d[TARGET],
        errors="coerce"
    )

    y = y.replace(
        [np.inf, -np.inf],
        np.nan
    )

    # --------------------------------------
    # 5. Identifier les lignes valides
    # --------------------------------------

    ok = (
        y.notna() &
        (y >= 0) &
        x.notna().any(axis=1)
    )

    # --------------------------------------
    # 6. Construire le dataset final
    # --------------------------------------

    resultat = x.loc[ok].copy()

    resultat[TARGET] = (
        y.loc[ok].astype(float)
    )

    # --------------------------------------
    # 7. Réinitialiser les index
    # --------------------------------------

    return resultat.reset_index(drop=True)
