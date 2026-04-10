from langchain_google_genai import ChatGoogleGenerativeAI

from aggregator import fetch_all_leagues_data
from models import LLMRankedMatchList, Match, RankedMatch
from prompts import ranking_prompt, format_league_data


def run_pipeline() -> list[RankedMatch]:
    """Fetch data, rank fixtures, and return sorted list of RankedMatch."""
    data = fetch_all_leagues_data()

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

    # Join LLM rankings back to original Match objects (preserving correct dates)
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
