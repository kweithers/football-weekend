from datetime import timezone
from models import RankedMatch

CATEGORY_BADGES = {
    "title": "[TITLE]",
    "champions_league": "[UCL]",
    "relegation": "[RELEGATION]",
    "six_pointer": "[SIX-POINTER]",
    "other": "[OTHER]",
}

LEAGUE_NAMES = {
    "PL": "Premier League",
    "PD": "La Liga",
    "BL1": "Bundesliga",
    "SA": "Serie A",
    "FL1": "Ligue 1",
}


def _day_label(ranked: RankedMatch) -> str:
    kickoff = ranked.match.kickoff
    return kickoff.astimezone(timezone.utc).strftime("%A %d %b")


def print_rankings(matches: list[RankedMatch], top_n: int = 10) -> None:
    shown = matches[:top_n]

    # Group by day
    days: dict[str, list[RankedMatch]] = {}
    for m in shown:
        day = _day_label(m)
        days.setdefault(day, []).append(m)

    print("\n" + "=" * 60)
    print("  WEEKEND FOOTBALL RANKINGS")
    print("=" * 60)

    for day, day_matches in days.items():
        print(f"\n  {day.upper()}")
        print("  " + "-" * 56)
        for rm in day_matches:
            badge = CATEGORY_BADGES.get(rm.category, "[OTHER]")
            league = LEAGUE_NAMES.get(rm.match.competition, rm.match.competition)
            kickoff = rm.match.kickoff.strftime("%H:%M UTC")
            score_bar = "█" * rm.excitement_score + "░" * (10 - rm.excitement_score)

            print(f"\n  {rm.excitement_score:>2}/10 {score_bar}  {badge}")
            print(f"  {rm.match.home_team} vs {rm.match.away_team}")
            print(f"  {league} · Matchday {rm.match.matchday} · {kickoff}")
            print(f"  {rm.reasoning}")

    print("\n" + "=" * 60 + "\n")
