"""Clean and join FRED series into a monthly modeling dataset."""

from pathlib import Path
from functools import reduce
from typing import Optional

import pandas as pd

from backend.data_fetcher import fetch_all_series


PROCESSED_DATA_DIR = Path(__file__).parent / "data" / "processed"
PROCESSED_DATA_PATH = PROCESSED_DATA_DIR / "monthly_housing_data.csv"


def _to_monthly(series: pd.DataFrame, value_column: str) -> pd.DataFrame:
    """Convert a date/value FRED series into month-start observations."""
    monthly = series.copy()
    monthly["date"] = monthly["date"].dt.to_period("M").dt.to_timestamp()
    monthly = monthly.sort_values("date")

    # Weekly mortgage rates become monthly averages. Monthly series are unchanged.
    return monthly.groupby("date", as_index=False)[value_column].mean()


def build_monthly_dataset(refresh: bool = False) -> pd.DataFrame:
    """Fetch, join, clean, and cache the monthly housing market dataset."""
    PROCESSED_DATA_DIR.mkdir(parents=True, exist_ok=True)

    if PROCESSED_DATA_PATH.exists() and not refresh:
        return pd.read_csv(PROCESSED_DATA_PATH, parse_dates=["date"])

    raw_series = fetch_all_series(refresh=refresh)
    monthly_frames = [
        _to_monthly(frame, column_name)
        for column_name, frame in raw_series.items()
    ]

    dataset = reduce(
        lambda left, right: pd.merge(left, right, on="date", how="outer"),
        monthly_frames,
    )
    dataset = dataset.sort_values("date")

    # Keep only months where every source has an actual observation. This avoids
    # treating stale values as if they were newly reported data.
    dataset = dataset.dropna().reset_index(drop=True)

    dataset["home_price_change"] = dataset["home_price_index"].pct_change() * 100
    dataset["housing_starts_change"] = dataset["housing_starts"].pct_change() * 100
    dataset["building_permits_change"] = dataset["building_permits"].pct_change() * 100
    dataset["mortgage_rate_change"] = dataset["mortgage_rate"].diff()
    dataset = dataset.dropna().reset_index(drop=True)

    dataset.to_csv(PROCESSED_DATA_PATH, index=False)
    return dataset


def records_for_api(dataset: pd.DataFrame, months: Optional[int] = None) -> list[dict]:
    """Convert the monthly dataset into JSON-friendly records."""
    api_frame = dataset.copy()
    if months:
        api_frame = api_frame.tail(months)
    api_frame["date"] = api_frame["date"].dt.strftime("%Y-%m-%d")
    return api_frame.round(4).to_dict(orient="records")
