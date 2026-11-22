
# ==========================================
# AGRIYIELD MLOPS - VALIDATION DES DONNEES
# Fichier : api/schemas.py
# ==========================================

from typing import Optional
import math

from pydantic import (
    BaseModel,
    ConfigDict,
    ValidationError,
    field_validator,
    model_validator
)


# ==========================================
# 1. CARACTERISTIQUES ATTENDUES
# ==========================================

# Les 8 caractéristiques utilisées par le modèle V1.
# Yield ne doit PAS être ajouté à cette liste.

COLONNES_ATTENDUES = [
    "Crop",
    "Season",
    "State",
    "Crop_Year",
    "Area",
    "Annual_Rainfall",
    "Fertilizer",
    "Pesticide"
]

# Champ supplémentaire facultatif.
# Utilisé pour stocker le rendement réel.

COLONNE_RENDEMENT_REEL = "Yield"

CHAMPS_CATEGORIELS = [
    "Crop",
    "Season",
    "State"
]

CHAMPS_NUMERIQUES = [
    "Crop_Year",
    "Area",
    "Annual_Rainfall",
    "Fertilizer",
    "Pesticide"
]

MAX_VALEURS_MANQUANTES = 3

ANNEE_MIN = 1900
ANNEE_MAX = 2100

VALEURS_MANQUANTES = {
    "",
    "null",
    "none",
    "nan",
    "na"
}


# ==========================================
# 2. SCHEMA D'UNE OBSERVATION
# ==========================================

class ObservationSchema(BaseModel):

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True
    )

    # --------------------------------------
    # Variables catégorielles
    # --------------------------------------

    Crop: Optional[str] = None
    Season: Optional[str] = None
    State: Optional[str] = None

    # --------------------------------------
    # Année de culture
    # --------------------------------------

    Crop_Year: Optional[int] = None

    # --------------------------------------
    # Variables numériques du modèle
    # --------------------------------------

    Area: Optional[float] = None
    Annual_Rainfall: Optional[float] = None
    Fertilizer: Optional[float] = None
    Pesticide: Optional[float] = None

    # --------------------------------------
    # Rendement réel facultatif
    # --------------------------------------

    # Yield n'est PAS une entrée du modèle.
    #
    # Valeurs autorisées :
    #   - None : rendement réel inconnu
    #   - 0 : rendement réel nul
    #   - nombre positif
    #
    # Correspondance MariaDB :
    #   Yield -> observations.rendement_reel

    Yield: Optional[float] = None

    # ======================================
    # NORMALISATION DES VALEURS MANQUANTES
    # ======================================

    @field_validator(
        *COLONNES_ATTENDUES,
        COLONNE_RENDEMENT_REEL,
        mode="before"
    )
    @classmethod
    def normaliser_valeurs(cls, valeur):

        if valeur is None:
            return None

        if isinstance(valeur, str):

            valeur = valeur.strip()

            if valeur.lower() in VALEURS_MANQUANTES:
                return None

            return valeur

        return valeur

    # ======================================
    # VERIFICATION DES CHAMPS CATEGORIELS
    # ======================================

    @field_validator(
        "Crop",
        "Season",
        "State",
        mode="before"
    )
    @classmethod
    def verifier_categories(cls, valeur, info):

        if valeur is None:
            return None

        if not isinstance(valeur, str):

            raise ValueError(
                f"{info.field_name} doit être un texte."
            )

        valeur = valeur.strip()

        if valeur.lower() in VALEURS_MANQUANTES:
            return None

        # Même normalisation que nettoyer_features().
        valeur = valeur.title()

        return valeur

    # ======================================
    # VERIFICATION DE L'ANNEE
    # ======================================

    @field_validator(
        "Crop_Year",
        mode="before"
    )
    @classmethod
    def verifier_annee(cls, valeur):

        if valeur is None:
            return None

        if isinstance(valeur, bool):

            raise ValueError(
                "Crop_Year doit être une année entière."
            )

        try:

            nombre = float(valeur)

        except (ValueError, TypeError, OverflowError):

            raise ValueError(
                "Crop_Year doit être une année entière."
            )

        if not math.isfinite(nombre):

            raise ValueError(
                "Crop_Year doit être un nombre fini."
            )

        if not nombre.is_integer():

            raise ValueError(
                "Crop_Year doit être une année entière."
            )

        annee = int(nombre)

        if not (ANNEE_MIN <= annee <= ANNEE_MAX):

            raise ValueError(
                f"Crop_Year doit être compris "
                f"entre {ANNEE_MIN} et {ANNEE_MAX}."
            )

        return annee

    # ======================================
    # VERIFICATION DES VARIABLES NUMERIQUES
    # ======================================

    @field_validator(
        "Area",
        "Annual_Rainfall",
        "Fertilizer",
        "Pesticide",
        mode="before"
    )
    @classmethod
    def verifier_numeriques(cls, valeur, info):

        if valeur is None:
            return None

        if isinstance(valeur, bool):

            raise ValueError(
                f"{info.field_name} doit être un nombre."
            )

        try:

            nombre = float(valeur)

        except (ValueError, TypeError, OverflowError):

            raise ValueError(
                f"{info.field_name} doit être un nombre."
            )

        if not math.isfinite(nombre):

            raise ValueError(
                f"{info.field_name} doit être un nombre fini."
            )

        if nombre < 0:

            raise ValueError(
                f"{info.field_name} doit être "
                "positif ou nul."
            )

        return nombre

    # ======================================
    # VERIFICATION DU RENDEMENT REEL YIELD
    # ======================================

    @field_validator(
        "Yield",
        mode="before"
    )
    @classmethod
    def verifier_yield(cls, valeur):

        # Yield est facultatif.
        # Une valeur manquante devient None.

        if valeur is None:
            return None

        if isinstance(valeur, str):

            valeur = valeur.strip()

            if valeur.lower() in VALEURS_MANQUANTES:
                return None

        # Refuser les booléens.
        if isinstance(valeur, bool):

            raise ValueError(
                "Yield doit être un nombre."
            )

        # Convertir en nombre.
        try:

            nombre = float(valeur)

        except (ValueError, TypeError, OverflowError):

            raise ValueError(
                "Yield doit être un nombre."
            )

        # Refuser NaN et les valeurs infinies.
        if not math.isfinite(nombre):

            raise ValueError(
                "Yield doit être un nombre fini."
            )

        # Autoriser 0 et les valeurs positives.
        if nombre < 0:

            raise ValueError(
                "Yield doit être positif ou nul."
            )

        return nombre

    # ======================================
    # MAXIMUM 3 CHAMPS MANQUANTS
    # ======================================

    @model_validator(mode="after")
    def verifier_valeurs_manquantes(self):

        # Compter uniquement les 8 caractéristiques.
        # Yield n'entre pas dans ce calcul.

        nombre_manquants = sum(
            getattr(self, colonne) is None
            for colonne in COLONNES_ATTENDUES
        )

        if nombre_manquants > MAX_VALEURS_MANQUANTES:

            raise ValueError(
                f"{nombre_manquants} champs manquants. "
                f"Maximum autorisé : "
                f"{MAX_VALEURS_MANQUANTES}."
            )

        return self

    # ======================================
    # EXTRAIRE LES 8 CARACTERISTIQUES
    # ======================================

    def donnees_pour_modele(self):
        """
        Retourne uniquement les 8 caractéristiques
        nécessaires au modèle V1.

        Yield est exclu.
        """

        return self.model_dump(
            include=set(COLONNES_ATTENDUES)
        )

    # ======================================
    # EXTRAIRE LE RENDEMENT REEL
    # ======================================

    def obtenir_rendement_reel(self):
        """
        Retourne le rendement réel facultatif.

        - None si Yield est absent
        - 0.0 si Yield vaut zéro
        - float positif sinon
        """

        return self.Yield


# ==========================================
# 3. VALIDATION D'UNE LIGNE CSV
# ==========================================

def valider_ligne_csv(ligne: dict):
    """
    Valide une observation CSV.

    Les 8 caractéristiques sont destinées
    au modèle de prédiction.

    Yield est facultatif et sert uniquement
    au stockage du rendement réel.

    Retour :
        {
            "statut": "acceptee" ou "refusee",
            "donnees": dictionnaire ou None,
            "motif": message ou None
        }
    """

    try:

        observation = ObservationSchema.model_validate(
            ligne
        )

        # Inclut les 8 caractéristiques et Yield.
        # Si Yield est absent, sa valeur sera None.

        donnees_validees = observation.model_dump()

        return {
            "statut": "acceptee",
            "donnees": donnees_validees,
            "motif": None
        }

    except ValidationError as erreur:

        motifs = []

        for item in erreur.errors():

            emplacement = item.get("loc", ())

            champ = (
                ".".join(
                    str(partie)
                    for partie in emplacement
                )
                if emplacement
                else "Observation"
            )

            message = str(
                item.get("msg", "Valeur invalide.")
            )

            motifs.append(
                f"{champ} : {message}"
            )

        return {
            "statut": "refusee",
            "donnees": None,
            "motif": " ; ".join(motifs)
        }
