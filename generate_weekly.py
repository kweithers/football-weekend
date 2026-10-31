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


BREAKS_FILE = "data/breaks.json"


def save_break_message(weekend_date: str, message: str) -> None:
    """Record why a weekend has no fixtures in data/breaks.json, keyed by weekend date."""
    breaks = {}
    if os.path.exists(BREAKS_FILE):
        with open(BREAKS_FILE) as f:
            breaks = json.load(f)
    breaks[weekend_date] = message
    with open(BREAKS_FILE, "w") as f:
        json.dump(breaks, f, indent=2, sort_keys=True)


def main() -> None:
    from pipeline import explain_empty_weekend, run_pipeline
    from tools import _get_weekend_range

    print("Running weekly ranking pipeline...")
    ranked = run_pipeline()

    os.makedirs("data", exist_ok=True)
    weekend_date = next_friday()
    filename = f"data/weekend_{weekend_date}.json"

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

    if not payload:
        message = explain_empty_weekend(*_get_weekend_range())
        save_break_message(weekend_date, message)
        print(f"No fixtures this week: {message}")


if __name__ == "__main__":
    main()
