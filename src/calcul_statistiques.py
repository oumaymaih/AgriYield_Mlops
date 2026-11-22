import numpy as np
import pandas as pd

from nettoyage_dataset import NUMERIC, CATEGORICAL, TARGET


def statistiques(df, bornes_reference=None):
    """
    Calculer les statistiques descriptives d'un dataset.

    T0 :
        statistiques(train)

    T1 :
        statistiques(
            production,
            bornes_reference=stats_T0
        )

    Si des bornes de référence sont fournies,
    les histogrammes utilisent les mêmes intervalles
    qu'à T0 afin de faciliter la comparaison.
    """

    out = {
        "effectif": int(len(df)),
        "variables": {}
    }

    for colonne in df.columns:

        s = df[colonne]

        d = {
            "type": str(s.dtype),
            "effectif_total": int(len(s)),
            "effectif_non_manquant": int(s.notna().sum()),
            "manquants": int(s.isna().sum()),
            "taux_manquants": (
                float(s.isna().mean())
                if len(s) else 0.0
            ),
            "nombre_valeurs_uniques": int(
                s.nunique(dropna=True)
            )
        }

        # -----------------------------------------------
        # VARIABLES NUMÉRIQUES
        # -----------------------------------------------

        if colonne in NUMERIC or colonne == TARGET:

            v = pd.to_numeric(
                s, errors="coerce"
            ).replace(
                [np.inf, -np.inf], np.nan
            ).dropna()

            d["effectif_non_manquant"] = int(len(v))
            d["manquants"] = int(len(s) - len(v))

            d["taux_manquants"] = (
                float((len(s) - len(v)) / len(s))
                if len(s) else 0.0
            )

            if len(v):

                q = v.quantile([
                    0, 0.01, 0.05, 0.10,
                    0.25, 0.50, 0.75,
                    0.90, 0.95, 0.99, 1
                ])

                q1 = float(q.loc[0.25])
                q3 = float(q.loc[0.75])

                iqr = q3 - q1

                moyenne = float(v.mean())

                ecart_type = (
                    float(v.std())
                    if len(v) > 1 else 0.0
                )

                borne_inf = q1 - 1.5 * iqr
                borne_sup = q3 + 1.5 * iqr

                # Bornes T0 réutilisées pour T1
                ref = (
                    bornes_reference
                    .get("variables", {})
                    .get(colonne, {})
                    if bornes_reference is not None
                    else {}
                )

                if "bornes_histogramme" in ref:

                    bornes = np.array(
                        ref["bornes_histogramme"],
                        dtype=float
                    )

                else:

                    bornes = np.histogram_bin_edges(
                        v,
                        bins=20
                    )

                # Gérer les colonnes constantes
                if len(bornes) < 2 or not (
                    np.diff(bornes) > 0
                ).all():
                    valeur = float(v.iloc[0])
                    bornes = np.linspace(
                        valeur - 0.5,
                        valeur + 0.5,
                        21
                    )

                effectifs, _ = np.histogram(
                    v,
                    bins=bornes
                )

                sous_min = int(
                    (v < bornes[0]).sum()
                )

                sur_max = int(
                    (v > bornes[-1]).sum()
                )

                d.update({
                    "moyenne": moyenne,
                    "mediane": float(v.median()),
                    "variance": (
                        float(v.var())
                        if len(v) > 1 else 0.0
                    ),
                    "ecart_type": ecart_type,
                    "min": float(v.min()),
                    "max": float(v.max()),
                    "etendue": float(
                        v.max() - v.min()
                    ),
                    "quartiles_quantiles": {
                        str(k): float(z)
                        for k, z in q.items()
                    },
                    "iqr": float(iqr),
                    "skewness": (
                        float(v.skew())
                        if len(v) >= 3 and v.nunique() > 1
                        else None
                    ),
                    "kurtosis": (
                        float(v.kurt())
                        if len(v) >= 4 and v.nunique() > 1
                        else None
                    ),
                    "borne_inferieure_iqr": float(
                        borne_inf
                    ),
                    "borne_superieure_iqr": float(
                        borne_sup
                    ),
                    "nombre_outliers_iqr": int(
                        (
                            (v < borne_inf) |
                            (v > borne_sup)
                        ).sum()
                    ),
                    "bornes_histogramme": bornes.tolist(),
                    "effectifs_histogramme": effectifs.tolist(),
                    "proportions_histogramme": (
                        effectifs / len(v)
                    ).tolist(),
                    "effectif_sous_min_histogramme": sous_min,
                    "effectif_sur_max_histogramme": sur_max
                })

        # -----------------------------------------------
        # VARIABLES CATÉGORIELLES
        # -----------------------------------------------

        else:

            counts = (
                s.astype("string")
                .fillna("<MANQUANT>")
                .value_counts()
            )

            d.update({
                "nombre_categories": int(
                    s.nunique(dropna=True)
                ),
                "mode": (
                    str(counts.index[0])
                    if len(counts) else None
                ),
                "effectifs": {
                    str(k): int(v)
                    for k, v in counts.items()
                },
                "proportions": {
                    str(k): float(v / len(s))
                    for k, v in counts.items()
                }
            })

        out["variables"][colonne] = d

    return out
