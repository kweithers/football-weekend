from langchain_google_genai import ChatGoogleGenerativeAI

from aggregator import fetch_all_leagues_data
from models import RankedMatch, RankedMatchList
from prompts import ranking_prompt, format_league_data


def run_pipeline() -> list[RankedMatch]:
    """Fetch data, rank fixtures, and return sorted list of RankedMatch."""
    data = fetch_all_leagues_data()
    league_data_str = format_league_data(data)

    llm = ChatGoogleGenerativeAI(model="gemini-3-flash-preview")
    structured_llm = llm.with_structured_output(RankedMatchList)

    chain = ranking_prompt | structured_llm

    result: RankedMatchList = chain.invoke({"league_data": league_data_str})
    return sorted(result.matches, key=lambda m: m.excitement_score, reverse=True)
