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


def main() -> None:
    from pipeline import run_pipeline

    print("Running weekly ranking pipeline...")
    ranked = run_pipeline()

    os.makedirs("data", exist_ok=True)
    filename = f"data/weekend_{next_friday()}.json"

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


if __name__ == "__main__":
    main()
