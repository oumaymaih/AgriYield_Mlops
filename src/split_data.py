import numpy as np
import pandas as pd

from sklearn.model_selection import train_test_split


def creer_strates_yield(df, n_groupes=10):
    '''
    Créer une stratification globale de Yield.

    Les intervalles sont calculés une seule fois
    et réutilisés pour tous les découpages.

    Les strates trop petites sont regroupées.
    '''

    if "Yield" not in df.columns:
        raise ValueError("La colonne Yield est absente.")

    y = pd.to_numeric(df["Yield"], errors="coerce")

    if y.isna().any():
        raise ValueError("Yield contient des valeurs manquantes.")

    if not np.isfinite(y).all():
        raise ValueError("Yield contient des valeurs non finies.")

    # Réduire progressivement le nombre de groupes
    for q in range(min(n_groupes, len(df) // 10), 1, -1):

        try:
            strates = pd.qcut(
                y,
                q=q,
                labels=False,
                duplicates="drop"
            )

            effectifs = strates.value_counts()

            # Minimum de 10 observations par strate
            if (
                strates.nunique() >= 2
                and effectifs.min() >= 10
            ):
                return strates.astype(int)

        except ValueError:
            continue

    raise ValueError(
        "Impossible de créer une stratification fiable "
        "sur Yield avec au moins 10 observations par strate."
    )


def partager(df, seed=42):
    '''
    Répartition :
    - Train : 60%
    - Validation : 10%
    - Test : 10%
    - Simulation : 20%

    Stratification globale sur Yield.
    '''

    donnees = df.copy().reset_index(drop=True)

    # Créer une seule fois les groupes
    donnees["_strate_yield"] = creer_strates_yield(
        donnees,
        n_groupes=10
    )

    # 1. Séparer Simulation : 20%
    reste, simulation = train_test_split(
        donnees,
        test_size=0.20,
        random_state=seed,
        stratify=donnees["_strate_yield"]
    )

    # 2. Séparer Test : 10% du total
    trainval, test = train_test_split(
        reste,
        test_size=0.125,
        random_state=seed,
        stratify=reste["_strate_yield"]
    )

    # 3. Séparer Validation : 10% du total
    train, validation = train_test_split(
        trainval,
        test_size=1/7,
        random_state=seed,
        stratify=trainval["_strate_yield"]
    )

    # Retirer la colonne temporaire
    def finaliser(partition):
        return (
            partition
            .drop(columns=["_strate_yield"])
            .reset_index(drop=True)
        )

    return (
        finaliser(train),
        finaliser(validation),
        finaliser(test),
        finaliser(simulation)
    )
