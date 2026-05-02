# Housing Demand Forecaster

A local full-stack learning project that analyzes public U.S. housing market data from FRED and produces a simple dashboard with trends, forecasts, and analyst-style insights.

The first version is intentionally small and explainable:

- Backend: FastAPI
- Frontend: plain HTML, CSS, and JavaScript
- Data analysis: pandas and numpy
- Modeling: scikit-learn
- Charts: Chart.js
- Storage: local CSV files

## Data Series

The app starts with these public FRED series:

- `HOUST`: Housing starts
- `PERMIT`: Building permits
- `MORTGAGE30US`: 30-year fixed mortgage rate
- `CSUSHPINSA`: Case-Shiller U.S. home price index

FRED CSV downloads are public and do not require a paid API key for this project.

## Project Structure

```text
housing-demand-forecaster/
  README.md
  requirements.txt
  .gitignore
  backend/
    main.py
    data_fetcher.py
    data_processing.py
    modeling.py
    insights.py
    data/
      raw/
      processed/
  frontend/
    index.html
    styles.css
    app.js
```

## Install

Create and activate a virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

## Run Locally

Start the FastAPI app:

```bash
uvicorn backend.main:app --reload
```

If your local environment blocks the file watcher used by `--reload`, run:

```bash
uvicorn backend.main:app
```

Open the dashboard in your browser:

```text
http://127.0.0.1:8000
```

The first request may take a few seconds because the backend downloads the FRED CSV files and writes local cache files. Later requests reuse those files unless you call the API with `?refresh=true`.

## API Endpoints

- `GET /api/data`: returns the joined monthly dataset.
- `GET /api/data?refresh=true`: re-downloads FRED data before returning the dataset.
- `GET /api/forecast`: trains a simple regression model and predicts the next-period Case-Shiller home price index change.
- `GET /api/insights`: returns rule-based analyst commentary based on recent trends.

## Notes for Learning

The code is split by responsibility:

- `data_fetcher.py` downloads and caches raw FRED CSV files.
- `data_processing.py` joins, cleans, and prepares monthly data.
- `modeling.py` creates lagged features and trains the simple forecast model.
- `insights.py` produces readable rule-based commentary.
- `main.py` exposes everything through FastAPI.

No authentication, database, deployment, or paid APIs are included in this MVP.
