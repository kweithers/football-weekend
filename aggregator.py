from tools import get_weekend_fixtures, get_standings, LEAGUE_CODES


def fetch_all_leagues_data() -> dict:
    """Loop through all 5 leagues and assemble fixtures + standings.

    Skips leagues with no fixtures (e.g. international breaks).
    Returns: {league_code: {"fixtures": [...], "standings": [...]}}
    """
    result = {}
    for code in LEAGUE_CODES:
        fixtures = get_weekend_fixtures.invoke(code)
        if not fixtures:
            continue
        standings = get_standings.invoke(code)
        result[code] = {"fixtures": fixtures, "standings": standings}
    return result
