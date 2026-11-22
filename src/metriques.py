import numpy as np

from sklearn.metrics import (
    r2_score,
    mean_absolute_error,
    mean_squared_error,
    median_absolute_error
)


def metriques_regression(y_true, y_pred):

    mse = mean_squared_error(y_true, y_pred)

    return {
        "n": int(len(y_true)),
        "r2": float(r2_score(y_true, y_pred)),
        "mae": float(mean_absolute_error(y_true, y_pred)),
        "rmse": float(np.sqrt(mse)),
        "medae": float(median_absolute_error(y_true, y_pred))
    }
