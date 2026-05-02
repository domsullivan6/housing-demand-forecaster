"""FastAPI entry point for the Housing Demand Forecaster backend."""

from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from backend.data_processing import build_monthly_dataset, records_for_api
from backend.insights import generate_insights
from backend.modeling import train_custom_model, train_forecast_model


load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent
FRONTEND_DIR = BASE_DIR / "frontend"


class LagFeatureRequest(BaseModel):
    """User-selected source column and month lag for the model hub."""

    source: str
    lag: int = Field(ge=1, le=24)


class ModelTrainingRequest(BaseModel):
    """Payload for the interactive model hub training endpoint."""

    features: list[str] = Field(default_factory=list)
    lag_features: list[LagFeatureRequest] = Field(default_factory=list)
    algorithm: str

app = FastAPI(
    title="Housing Demand Forecaster",
    description="A local learning app for U.S. housing market trends and forecasts.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")


def _json_ready_latest(row) -> dict:
    """Round numeric latest values while preserving the date string."""
    output = {}
    for key, value in row.items():
        if key == "date":
            output[key] = value.strftime("%Y-%m-%d")
        elif hasattr(value, "item"):
            output[key] = round(float(value), 4)
        else:
            output[key] = value
    return output


@app.get("/")
def dashboard() -> FileResponse:
    """Serve the frontend dashboard."""
    return FileResponse(FRONTEND_DIR / "index.html")


@app.get("/api/data")
def get_data(
    refresh: bool = Query(default=False),
    months: Optional[int] = Query(default=None, ge=12, le=600),
) -> dict:
    """Return the joined monthly housing dataset."""
    dataset = build_monthly_dataset(refresh=refresh)

    return {
        "series": records_for_api(dataset, months=months),
        "latest": _json_ready_latest(dataset.iloc[-1]),
        "row_count": len(dataset),
        "returned_rows": len(dataset.tail(months)) if months else len(dataset),
    }


@app.get("/api/forecast")
def get_forecast(refresh: bool = Query(default=False)) -> dict:
    """Train the MVP model and return the next-period home price change forecast."""
    dataset = build_monthly_dataset(refresh=refresh)
    return train_forecast_model(dataset)


@app.get("/api/insights")
def get_insights(refresh: bool = Query(default=False)) -> dict:
    """Return rule-based analyst commentary about current housing trends."""
    dataset = build_monthly_dataset(refresh=refresh)
    return {
        "latest_date": dataset["date"].iloc[-1].strftime("%Y-%m-%d"),
        "insights": generate_insights(dataset),
    }


@app.post("/api/model/train")
def train_model(request: ModelTrainingRequest) -> dict:
    """Train a user-configured model for the machine learning hub."""
    dataset = build_monthly_dataset()

    try:
        return train_custom_model(
            dataset=dataset,
            features=request.features,
            lag_features=[lag.model_dump() for lag in request.lag_features],
            algorithm=request.algorithm,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
