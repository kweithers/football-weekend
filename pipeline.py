from langchain_google_genai import ChatGoogleGenerativeAI

from aggregator import fetch_all_leagues_data
from models import LLMRankedMatchList, Match, RankedMatch
from prompts import break_prompt, ranking_prompt, format_league_data


def run_pipeline() -> list[RankedMatch]:
    """Fetch data, rank fixtures, and return sorted list of RankedMatch.

    Returns an empty list only when football-data.org has no fixtures for any
    league. Raises if fixtures exist but none could be ranked.
    """
    data = fetch_all_leagues_data()
    if not data:
        return []

    # Build a lookup of all matches keyed by (home_team, away_team, competition)
    all_matches: dict[tuple[str, str, str], Match] = {}
    for league_code, content in data.items():
        for match in content["fixtures"]:
            all_matches[(match.home_team, match.away_team, match.competition)] = match

    league_data_str = format_league_data(data)

    llm = ChatGoogleGenerativeAI(model="gemini-3-flash-preview")
    structured_llm = llm.with_structured_output(LLMRankedMatchList)

    chain = ranking_prompt | structured_llm

    result: LLMRankedMatchList = chain.invoke({"league_data": league_data_str})

    ranked = _build_ranked_matches(all_matches, result)

    if not ranked:
        fixture_count = len(all_matches)
        raise RuntimeError(f"Ranking failed: {fixture_count} fixtures fetched but none were ranked")

    return ranked


def _build_ranked_matches(
    all_matches: dict[tuple[str, str, str], Match],
    result: LLMRankedMatchList,
) -> list[RankedMatch]:
    """Join LLM rankings back to original Match objects and sort by score."""
    ranked = []
    for r in result.matches:
        match = all_matches.get((r.home_team, r.away_team, r.competition))
        if match is None:
            continue
        ranked.append(RankedMatch(
            match=match,
            excitement_score=r.excitement_score,
            category=r.category,
            reasoning=r.reasoning,
        ))
    return sorted(ranked, key=lambda m: m.excitement_score, reverse=True)


def explain_empty_weekend(date_from: str, date_to: str) -> str:
    """Ask Gemini, grounded with Google Search, why there are no league fixtures in the range."""
    llm = ChatGoogleGenerativeAI(model="gemini-3-flash-preview")
    search_llm = llm.bind_tools([{"google_search": {}}])

    chain = break_prompt | search_llm

    result = chain.invoke({"date_from": date_from, "date_to": date_to})
    return result.text.strip()
