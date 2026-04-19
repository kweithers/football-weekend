# Football Weekend Ranker

Ranks the weekend's top European football fixtures by how consequential they are — title races, Champions League battles, relegation scraps — using live data from football-data.org and Gemini.

## Running

### Terminal output

Fetches live fixtures and standings, ranks them, and prints to the terminal:

```bash
uv run python main.py
```

### Generate weekly JSON

Runs the pipeline and writes ranked fixtures to `data/weekend_YYYY-MM-DD.json`:

```bash
uv run python generate_weekly.py
```

### Web app

Serves the rankings as a web page at `http://localhost:8000`. Requires a JSON file in `data/` (run `generate_weekly.py` first).

```bash
uv run uvicorn api:app --reload
```

The `/api/weekend` endpoint returns the raw JSON if you want to consume it programmatically.

## GitHub Actions (weekly automation)

The workflow in `.github/workflows/weekly.yml` runs every Tuesday at 07:00 UTC, generates fresh rankings, and commits the JSON back to the repo.

To enable it:

1. Go to your repo → **Settings → Secrets and variables → Actions**
2. Add two repository secrets:
   - `FOOTBALL_DATA_API_KEY`
   - `GOOGLE_API_KEY`
3. Push to GitHub — the cron will fire automatically on Tuesdays.

You can also trigger it manually from the **Actions** tab using the "Run workflow" button.
