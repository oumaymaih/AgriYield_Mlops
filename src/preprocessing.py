import joblib

from pathlib import Path
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import OneHotEncoder, PowerTransformer

from nettoyage_dataset import NUMERIC, CATEGORICAL, FEATURES


def creer_preprocessing():

    # Transformations numériques
    numerique = Pipeline([
        (
            "imputation",
            SimpleImputer(
                strategy="median",
                keep_empty_features=True
            )
        ),
        (
            "puissance",
            PowerTransformer(
                method="yeo-johnson",
                standardize=True
            )
        )
    ])

    # Transformations catégorielles
    categoriel = Pipeline([
        (
            "imputation",
            SimpleImputer(
                strategy="most_frequent",
                keep_empty_features=True
            )
        ),
        (
            "encodage",
            OneHotEncoder(
                handle_unknown="ignore"
            )
        )
    ])

    return ColumnTransformer(
        transformers=[
            ("numerique", numerique, NUMERIC),
            ("categoriel", categoriel, CATEGORICAL)
        ],
        remainder="drop"
    )


def entrainer_preprocessing(
    train,
    validation,
    test,
    simulation,
    chemin_pkl
):

    # Nouveau preprocessing non entraîné
    preprocessor = creer_preprocessing()

    # Apprentissage uniquement sur Train
    X_train = preprocessor.fit_transform(
        train[FEATURES]
    )

    # Application aux autres ensembles
    X_validation = preprocessor.transform(
        validation[FEATURES]
    )

    X_test = preprocessor.transform(
        test[FEATURES]
    )

    X_simulation = preprocessor.transform(
        simulation[FEATURES]
    )

    # Vérifier la cohérence des dimensions
    assert (
        X_train.shape[1]
        == X_validation.shape[1]
        == X_test.shape[1]
        == X_simulation.shape[1]
    )

    # Sauvegarder le preprocessing appris
    chemin_pkl = Path(chemin_pkl)
    chemin_pkl.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    joblib.dump(preprocessor, chemin_pkl)

    return (
        preprocessor,
        X_train,
        X_validation,
        X_test,
        X_simulation
    )
