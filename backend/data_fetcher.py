"""Download and cache public FRED housing and economic time series."""

from pathlib import Path

import pandas as pd


FRED_SERIES = {
    "HOUST": "housing_starts",
    "PERMIT": "building_permits",
    "MORTGAGE30US": "mortgage_rate",
    "CSUSHPINSA": "home_price_index",
}

RAW_DATA_DIR = Path(__file__).parent / "data" / "raw"


def fred_csv_url(series_id: str) -> str:
    """Build the public CSV download URL for a FRED series."""
    return f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={series_id}"


def fetch_series(series_id: str, refresh: bool = False) -> pd.DataFrame:
    """Return one FRED series as a DataFrame, using a local CSV cache when possible."""
    RAW_DATA_DIR.mkdir(parents=True, exist_ok=True)
    output_path = RAW_DATA_DIR / f"{series_id}.csv"

    if output_path.exists() and not refresh:
        raw = pd.read_csv(output_path)
    else:
        raw = pd.read_csv(fred_csv_url(series_id))
        raw.to_csv(output_path, index=False)

    date_column = "DATE" if "DATE" in raw.columns else "observation_date"
    raw[date_column] = pd.to_datetime(raw[date_column])
    raw[series_id] = pd.to_numeric(raw[series_id], errors="coerce")
    return raw.rename(columns={date_column: "date", series_id: FRED_SERIES[series_id]})


def fetch_all_series(refresh: bool = False) -> dict[str, pd.DataFrame]:
    """Fetch every configured FRED series and return them by friendly column name."""
    return {
        friendly_name: fetch_series(series_id, refresh=refresh)
        for series_id, friendly_name in FRED_SERIES.items()
    }
