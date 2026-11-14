"""FastAPI backend — serves pre-generated weekly rankings from data/."""
import json
import os
import re
from datetime import date, datetime
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse

from fastapi.templating import Jinja2Templates
from starlette.requests import Request

app = FastAPI(title="Football Weekend Ranker")
templates = Jinja2Templates(directory="templates")

DATA_DIR = Path("data")
EMPTY_WEEKENDS_FILE = DATA_DIR / "empty_weekends.json"
DEFAULT_EMPTY_WEEKEND = {"type": "break", "message": "No league fixtures this weekend."}

LEAGUE_NAMES = {
    "PL": "Premier League",
    "PD": "La Liga",
    "BL1": "Bundesliga",
    "SA": "Serie A",
    "FL1": "Ligue 1",
}

# flag-icons country codes (https://github.com/lipis/flag-icons)
LEAGUE_FLAGS = {
    "PL": "gb-eng",
    "PD": "es",
    "BL1": "de",
    "SA": "it",
    "FL1": "fr",
}


def _latest_data_file() -> Path | None:
    files = _weekend_files()
    return files[0] if files else None


WEEKEND_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def _weekend_files() -> list[Path]:
    """All weekend data files, newest first."""
    if not DATA_DIR.exists():
        return []
    return sorted(DATA_DIR.glob("weekend_*.json"), reverse=True)


def _weekend_dates() -> list[str]:
    """All weekend dates (YYYY-MM-DD) that have data, newest first."""
    return [p.stem.replace("weekend_", "") for p in _weekend_files()]


def _data_file_for(weekend_date: str) -> Path | None:
    """Data file for a given weekend date, or None if invalid / missing."""
    if not WEEKEND_DATE_RE.match(weekend_date):
        return None
    path = DATA_DIR / f"weekend_{weekend_date}.json"
    return path if path.exists() else None


def _weekend_label(weekend_date: str) -> str:
    return "Weekend of " + date.fromisoformat(weekend_date).strftime("%-d %b %Y")


def _load_matches(path: Path) -> list[dict]:
    """Load a weekend's matches, enriched for display and sorted by day then score."""
    with open(path) as f:
        matches = json.load(f)
    for m in matches:
        m["league_name"] = LEAGUE_NAMES.get(m["competition"], m["competition"])
        m["league_flag"] = LEAGUE_FLAGS.get(m["competition"])
        m["day_label"] = datetime.fromisoformat(m["kickoff"]).strftime("%A %-d %b")
    matches.sort(key=lambda m: (m["kickoff"][:10], -m["excitement_score"]))
    return matches


def _empty_weekend(weekend_date: str | None) -> dict:
    """Return why a weekend has no matches ({"type": "break" | "error", "message": str})."""
    if weekend_date and EMPTY_WEEKENDS_FILE.exists():
        with open(EMPTY_WEEKENDS_FILE) as f:
            weekends = json.load(f)
        return weekends.get(weekend_date, DEFAULT_EMPTY_WEEKEND)
    return DEFAULT_EMPTY_WEEKEND


@app.get("/api/weekend")
def get_weekend():
    path = _latest_data_file()
    if path is None:
        raise HTTPException(status_code=404, detail="No rankings generated yet")
    with open(path) as f:
        return json.load(f)


@app.get("/api/weekends")
def list_weekends():
    return _weekend_dates()


@app.get("/api/weekend/{weekend_date}")
def get_weekend_by_date(weekend_date: str):
    path = _data_file_for(weekend_date)
    if path is None:
        raise HTTPException(status_code=404, detail="No rankings for that weekend")
    with open(path) as f:
        return json.load(f)


def _render_weekend(request: Request, path: Path | None, is_archive: bool):
    matches = []
    weekend_date = None
    if path:
        matches = _load_matches(path)
        # Extract date from filename: weekend_YYYY-MM-DD.json
        weekend_date = path.stem.replace("weekend_", "")

    context = {
        "matches": matches,
        "weekend_date": weekend_date,
        "empty_weekend": None if matches else _empty_weekend(weekend_date),
        "is_archive": is_archive,
    }
    if is_archive and weekend_date:
        dates = _weekend_dates()  # newest first
        idx = dates.index(weekend_date)
        context.update(
            weekend_label=_weekend_label(weekend_date),
            weeks=[{"date": d, "label": _weekend_label(d)} for d in dates],
            newer_week=dates[idx - 1] if idx > 0 else None,
            older_week=dates[idx + 1] if idx + 1 < len(dates) else None,
        )
    return templates.TemplateResponse(request=request, name="index.html", context=context)


@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    return _render_weekend(request, _latest_data_file(), is_archive=False)


@app.get("/week/{weekend_date}", response_class=HTMLResponse)
def week(request: Request, weekend_date: str):
    path = _data_file_for(weekend_date)
    if path is None:
        raise HTTPException(status_code=404, detail="No rankings for that weekend")
    return _render_weekend(request, path, is_archive=True)


@app.get("/history", response_class=HTMLResponse)
def history(request: Request):
    weeks = []
    for path in _weekend_files():
        weekend_date = path.stem.replace("weekend_", "")
        matches = _load_matches(path)
        top = max(matches, key=lambda m: m["excitement_score"], default=None)
        weeks.append({
            "date": weekend_date,
            "label": _weekend_label(weekend_date),
            "match_count": len(matches),
            "bangers": sum(1 for m in matches if m["excitement_score"] >= 9),
            "top_match": top,
            "empty_weekend": None if matches else _empty_weekend(weekend_date),
        })
    return templates.TemplateResponse(
        request=request, name="history.html", context={"weeks": weeks}
    )
