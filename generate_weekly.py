"""Standalone job: runs the ranking pipeline and writes output to data/weekend_YYYY-MM-DD.json.

Run this every Friday morning (or via GitHub Actions cron).
"""
import json
import os
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv

load_dotenv()


def next_friday() -> str:
    today = datetime.now(timezone.utc)
    days_until_friday = (4 - today.weekday()) % 7
    friday = today + timedelta(days=days_until_friday)
    return friday.strftime("%Y-%m-%d")


EMPTY_WEEKENDS_FILE = "data/empty_weekends.json"
ERROR_MESSAGE = "Something went wrong generating this week's rankings. Check back soon."
FALLBACK_BREAK_MESSAGE = "No league fixtures this weekend."


def set_empty_weekend(weekend_date: str, entry: dict | None) -> None:
    """Record (or clear) why a weekend has no matches in data/empty_weekends.json.

    entry is {"type": "break" | "error", "message": str}, or None to remove the date.
    """
    weekends = {}
    if os.path.exists(EMPTY_WEEKENDS_FILE):
        with open(EMPTY_WEEKENDS_FILE) as f:
            weekends = json.load(f)
    if entry is None:
        weekends.pop(weekend_date, None)
    else:
        weekends[weekend_date] = entry
    with open(EMPTY_WEEKENDS_FILE, "w") as f:
        json.dump(weekends, f, indent=2, sort_keys=True)


def main() -> None:
    from pipeline import explain_empty_weekend, run_pipeline
    from tools import _get_weekend_range

    os.makedirs("data", exist_ok=True)
    weekend_date = next_friday()
    filename = f"data/weekend_{weekend_date}.json"

    print("Running weekly ranking pipeline...")
    try:
        ranked = run_pipeline()
    except Exception:
        # Don't clobber rankings from an earlier successful run for the same weekend
        if not os.path.exists(filename):
            with open(filename, "w") as f:
                json.dump([], f)
            set_empty_weekend(weekend_date, {"type": "error", "message": ERROR_MESSAGE})
        raise

    payload = [
        {
            "home_team": rm.match.home_team,
            "away_team": rm.match.away_team,
            "kickoff": rm.match.kickoff.isoformat(),
            "competition": rm.match.competition,
            "matchday": rm.match.matchday,
            "excitement_score": rm.excitement_score,
            "category": rm.category,
            "reasoning": rm.reasoning,
        }
        for rm in ranked
    ]

    with open(filename, "w") as f:
        json.dump(payload, f, indent=2)

    print(f"Written {len(payload)} matches to {filename}")

    if payload:
        set_empty_weekend(weekend_date, None)
        return

    # football-data.org genuinely returned no fixtures: find out why
    try:
        message = explain_empty_weekend(*_get_weekend_range())
    except Exception as e:
        print(f"Could not explain empty weekend: {e}")
        message = FALLBACK_BREAK_MESSAGE
    set_empty_weekend(weekend_date, {"type": "break", "message": message})
    print(f"No fixtures this week: {message}")


if __name__ == "__main__":
    main()
