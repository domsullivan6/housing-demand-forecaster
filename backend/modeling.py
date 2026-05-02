"""Train a simple explainable forecast model for home price index changes."""

import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, r2_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler


FEATURE_COLUMNS = [
    "housing_starts_lag1",
    "building_permits_lag1",
    "mortgage_rate_lag1",
    "home_price_change_lag1",
]


def create_modeling_frame(dataset: pd.DataFrame) -> pd.DataFrame:
    """Create lagged inputs and the next-period prediction target."""
    model_frame = dataset.copy()
    model_frame["housing_starts_lag1"] = model_frame["housing_starts"].shift(1)
    model_frame["building_permits_lag1"] = model_frame["building_permits"].shift(1)
    model_frame["mortgage_rate_lag1"] = model_frame["mortgage_rate"].shift(1)
    model_frame["home_price_change_lag1"] = model_frame["home_price_change"].shift(1)
    model_frame["target_next_home_price_change"] = model_frame["home_price_change"].shift(-1)
    return model_frame.dropna().reset_index(drop=True)


def train_forecast_model(dataset: pd.DataFrame) -> dict:
    """Train a small regression model and forecast the next home price index change."""
    model_frame = create_modeling_frame(dataset)

    if len(model_frame) < 24:
        raise ValueError("At least 24 monthly observations are required to train the model.")

    x = model_frame[FEATURE_COLUMNS]
    y = model_frame["target_next_home_price_change"]

    # Use shuffle=False because time series order matters for a realistic test split.
    x_train, x_test, y_train, y_test = train_test_split(
        x,
        y,
        test_size=0.2,
        shuffle=False,
    )

    model = make_pipeline(StandardScaler(), LinearRegression())
    model.fit(x_train, y_train)

    test_predictions = model.predict(x_test)
    latest_features = x.tail(1)
    forecast = float(model.predict(latest_features)[0])
    latest_date = model_frame["date"].iloc[-1]

    coefficients = model.named_steps["linearregression"].coef_
    importance_total = np.abs(coefficients).sum()
    if importance_total == 0:
        importance_total = 1
    importances = sorted(
        zip(FEATURE_COLUMNS, np.abs(coefficients) / importance_total),
        key=lambda item: item[1],
        reverse=True,
    )

    return {
        "latest_model_date": latest_date.strftime("%Y-%m-%d"),
        "forecast_next_home_price_change_pct": round(forecast, 3),
        "direction": "up" if forecast >= 0 else "down",
        "test_mae_pct_points": round(float(mean_absolute_error(y_test, test_predictions)), 3),
        "test_r2": round(float(r2_score(y_test, test_predictions)), 3),
        "training_rows": int(len(x_train)),
        "test_rows": int(len(x_test)),
        "feature_importance": [
            {"feature": feature, "importance": round(float(importance), 3)}
            for feature, importance in importances
        ],
        "latest_inputs": {
            key: round(float(value), 3)
            for key, value in latest_features.iloc[0].replace({np.nan: None}).items()
        },
    }
