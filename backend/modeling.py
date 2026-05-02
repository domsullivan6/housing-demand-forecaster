"""Train a simple explainable forecast model for home price index changes."""

import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, r2_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import GradientBoostingRegressor, RandomForestRegressor


FEATURE_COLUMNS = [
    "housing_starts_lag1",
    "building_permits_lag1",
    "mortgage_rate_lag1",
    "home_price_change_lag1",
]

ALGORITHMS = {
    "linear_regression": "Linear Regression",
    "gbm": "Gradient Boosting Machine",
    "random_forest": "Random Forest",
}


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


def train_custom_model(
    dataset: pd.DataFrame,
    features: list[str],
    lag_features: list[dict],
    algorithm: str,
) -> dict:
    """Train an interactive scikit-learn model from user-selected features."""
    if algorithm not in ALGORITHMS:
        raise ValueError("Unsupported algorithm.")

    if not features and not lag_features:
        raise ValueError("Select at least one base feature or lag feature.")

    model_frame = dataset.copy()
    selected_features = []

    for feature in features:
        if feature not in model_frame.columns:
            raise ValueError(f"Unknown feature: {feature}")
        selected_features.append(feature)

    for lag_config in lag_features:
        source = lag_config["source"]
        lag = int(lag_config["lag"])
        if source not in model_frame.columns:
            raise ValueError(f"Unknown lag source: {source}")
        if lag < 1 or lag > 24:
            raise ValueError("Lag values must be between 1 and 24 months.")

        lag_column = f"{source}_lag{lag}"
        model_frame[lag_column] = model_frame[source].shift(lag)
        selected_features.append(lag_column)

    # The MVP target is one-month-ahead Case-Shiller monthly percent change.
    model_frame["target_next_home_price_change"] = model_frame["home_price_change"].shift(-1)
    model_frame = model_frame.dropna(subset=selected_features + ["target_next_home_price_change"])

    if len(model_frame) < 24:
        raise ValueError("At least 24 complete rows are required after lag creation.")

    x = model_frame[selected_features]
    y = model_frame["target_next_home_price_change"]
    x_train, x_test, y_train, y_test = train_test_split(
        x,
        y,
        test_size=0.2,
        shuffle=False,
    )

    if algorithm == "linear_regression":
        model = make_pipeline(StandardScaler(), LinearRegression())
    elif algorithm == "gbm":
        model = GradientBoostingRegressor(random_state=42)
    else:
        model = RandomForestRegressor(
            n_estimators=200,
            max_depth=5,
            random_state=42,
        )

    model.fit(x_train, y_train)
    predictions = model.predict(x_test)
    residuals = y_test - predictions
    rmse = float(np.sqrt(np.mean(np.square(residuals))))

    explanation_rows = _model_explanation_rows(model, algorithm, selected_features)
    prediction_rows = [
        {
            "date": date.strftime("%Y-%m-%d"),
            "actual": round(float(actual), 4),
            "predicted": round(float(predicted), 4),
        }
        for date, actual, predicted in zip(model_frame.loc[y_test.index, "date"], y_test, predictions)
    ]

    return {
        "algorithm": ALGORITHMS[algorithm],
        "target": "Next-period Case-Shiller monthly percent change",
        "features": selected_features,
        "training_rows": int(len(x_train)),
        "test_rows": int(len(x_test)),
        "metrics": {
            "mae": round(float(mean_absolute_error(y_test, predictions)), 4),
            "rmse": round(rmse, 4),
            "r2": round(float(r2_score(y_test, predictions)), 4),
        },
        "explanation_label": "Coefficient" if algorithm == "linear_regression" else "Feature Importance",
        "explanation": explanation_rows,
        "predictions": prediction_rows,
    }


def _model_explanation_rows(model, algorithm: str, features: list[str]) -> list[dict]:
    """Return coefficients for linear regression or importances for tree models."""
    if algorithm == "linear_regression":
        values = model.named_steps["linearregression"].coef_
    else:
        values = model.feature_importances_

    return [
        {
            "feature": feature,
            "value": round(float(value), 4),
        }
        for feature, value in sorted(
            zip(features, values),
            key=lambda item: abs(item[1]),
            reverse=True,
        )
    ]
