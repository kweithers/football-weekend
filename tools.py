import os
import time
from datetime import datetime, timedelta, timezone

import requests
from langchain_core.tools import tool

from models import Match, TeamStanding

FOOTBALL_DATA_BASE_URL = "https://api.football-data.org/v4"
LEAGUE_CODES = ["PL", "PD", "BL1", "SA", "FL1"]


def _get_headers() -> dict:
    return {"X-Auth-Token": os.environ["FOOTBALL_DATA_API_KEY"]}


def _get_weekend_range() -> tuple[str, str]:
    """Return the upcoming Friday 00:00 UTC through Monday 00:00 UTC as date strings."""
    today = datetime.now(timezone.utc)
    # days_until_friday: 0=Mon,...,4=Fri
    days_until_friday = (4 - today.weekday()) % 7
    if days_until_friday == 0 and today.hour >= 0:
        # Already Friday or beyond — use this weekend
        pass
    friday = today + timedelta(days=days_until_friday)
    friday = friday.replace(hour=0, minute=0, second=0, microsecond=0)
    monday = friday + timedelta(days=3)
    return friday.strftime("%Y-%m-%d"), monday.strftime("%Y-%m-%d")


@tool
def get_weekend_fixtures(league_code: str) -> list[Match]:
    """Fetch weekend fixtures for a given league code from football-data.org.

    Args:
        league_code: One of PL, PD, BL1, SA, FL1
    """
    date_from, date_to = _get_weekend_range()
    url = f"{FOOTBALL_DATA_BASE_URL}/competitions/{league_code}/matches"
    params = {"dateFrom": date_from, "dateTo": date_to}
    resp = requests.get(url, headers=_get_headers(), params=params)
    resp.raise_for_status()
    data = resp.json()

    matches = []
    for m in data.get("matches", []):
        utc_date = m.get("utcDate", "")
        kickoff = datetime.fromisoformat(utc_date.replace("Z", "+00:00"))
        matches.append(
            Match(
                home_team=m["homeTeam"]["name"],
                away_team=m["awayTeam"]["name"],
                kickoff=kickoff,
                competition=league_code,
                matchday=m.get("matchday", 0),
            )
        )
    time.sleep(6)  # respect 10 req/min rate limit
    return matches


@tool
def get_standings(league_code: str) -> list[TeamStanding]:
    """Fetch current standings for a given league from football-data.org.

    Args:
        league_code: One of PL, PD, BL1, SA, FL1
    """
    url = f"{FOOTBALL_DATA_BASE_URL}/competitions/{league_code}/standings"
    resp = requests.get(url, headers=_get_headers())
    resp.raise_for_status()
    data = resp.json()

    standings = []
    for table in data.get("standings", []):
        if table.get("type") == "TOTAL":
            for entry in table.get("table", []):
                standings.append(
                    TeamStanding(
                        position=entry["position"],
                        team=entry["team"]["name"],
                        points=entry["points"],
                        played=entry["playedGames"],
                        goal_difference=entry["goalDifference"],
                    )
                )
            break
    time.sleep(6)
    return standings
