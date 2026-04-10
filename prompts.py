from langchain_core.prompts import ChatPromptTemplate

from models import Match, TeamStanding

RANKING_SYSTEM_PROMPT = """You are a football analyst who ranks weekend \
fixtures by how consequential they are for the league table. Your job is \
to identify matches with real stakes, NOT matches between famous clubs.

A match is exciting if and only if the RESULT meaningfully affects one of:

1. TITLE RACE: At least one team is in the top 3 AND within 6 points of 1st place.
2. CHAMPIONS LEAGUE RACE: At least one team is in positions 3-7 AND within 5 points
   of the Champions League cutoff for that league:
   - Premier League (PL): top 4 → 5th qualifies for Europa
   - La Liga (PD): top 4
   - Bundesliga (BL1): top 4
   - Serie A (SA): top 4
   - Ligue 1 (FL1): top 3
3. RELEGATION BATTLE: At least one team is in the bottom 6 AND within 5 points of
   the relegation zone (bottom 3 in all these leagues, except Bundesliga where
   it's bottom 2 + a playoff spot).
4. DIRECT SIX-POINTER: Both teams are competing for the same thing (both in title
   race, both fighting relegation, etc.). These are the most exciting of all.

CRITICAL RULES:
- Matchday context matters. Early season (matchday < 10), gaps are less meaningful —
  downweight accordingly. Late season (matchday > 28), gaps are nearly decisive —
  upweight accordingly.
- A match between two famous clubs with nothing to play for is NOT exciting.
  Liverpool vs Chelsea in 8th vs 11th is a 3/10, not a 9/10.
- A match between two unknown clubs fighting relegation on the final matchday IS
  exciting. That's a 9/10.
- Be harsh. Most weekend matches should score 3-5. Reserve 8+ for genuine stakes.

For each fixture provided, return:
- excitement_score: integer 1-10
- category: one of "title", "champions_league", "relegation", "six_pointer", "other"
- reasoning: ONE sentence explaining the specific stakes, citing positions and \
point gaps from the standings

Return ALL fixtures ranked from highest to lowest excitement_score."""

RANKING_USER_PROMPT = """Here is the weekend's data across the top 5 European leagues.

{league_data}

Rank every fixture by excitement score using the criteria above."""

ranking_prompt = ChatPromptTemplate.from_messages([
    ("system", RANKING_SYSTEM_PROMPT),
    ("user", RANKING_USER_PROMPT),
])


def format_league_data(data: dict) -> str:
    """Format aggregated league data into readable text for the LLM prompt."""
    lines = []
    for league_code, content in data.items():
        lines.append(f"=== {league_code} ===")

        standings: list[TeamStanding] = content["standings"]
        lines.append("Standings:")
        lines.append(f"{'Pos':<4} {'Team':<30} {'Pts':<5} {'Played':<7} {'GD'}")
        for s in standings:
            lines.append(f"{s.position:<4} {s.team:<30} {s.points:<5} {s.played:<7} {s.goal_difference:+d}")

        fixtures: list[Match] = content["fixtures"]
        lines.append("\nWeekend Fixtures:")
        for f in fixtures:
            kickoff_str = f.kickoff.strftime("%a %d %b %H:%M UTC")
            lines.append(f"  Matchday {f.matchday}: {f.home_team} vs {f.away_team} — {kickoff_str}")

        lines.append("")

    return "\n".join(lines)
