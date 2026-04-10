"""FastAPI backend — serves pre-generated weekly rankings from data/."""
import json
import os
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse

from fastapi.templating import Jinja2Templates
from starlette.requests import Request

app = FastAPI(title="Football Weekend Ranker")
templates = Jinja2Templates(directory="templates")

DATA_DIR = Path("data")

LEAGUE_NAMES = {
    "PL": "Premier League",
    "PD": "La Liga",
    "BL1": "Bundesliga",
    "SA": "Serie A",
    "FL1": "Ligue 1",
}


def _latest_data_file() -> Path | None:
    if not DATA_DIR.exists():
        return None
    files = sorted(DATA_DIR.glob("weekend_*.json"), reverse=True)
    return files[0] if files else None


@app.get("/api/weekend")
def get_weekend():
    path = _latest_data_file()
    if path is None:
        raise HTTPException(status_code=404, detail="No rankings generated yet")
    with open(path) as f:
        return json.load(f)


@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    path = _latest_data_file()
    matches = []
    weekend_date = None
    if path:
        with open(path) as f:
            matches = json.load(f)
        # Extract date from filename: weekend_YYYY-MM-DD.json
        weekend_date = path.stem.replace("weekend_", "")

    # Enrich with league names
    for m in matches:
        m["league_name"] = LEAGUE_NAMES.get(m["competition"], m["competition"])

    return templates.TemplateResponse(
        "index.html",
        {"request": request, "matches": matches, "weekend_date": weekend_date},
    )
