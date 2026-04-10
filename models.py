from pydantic import BaseModel
from datetime import datetime


class Match(BaseModel):
    home_team: str
    away_team: str
    kickoff: datetime
    competition: str
    matchday: int


class TeamStanding(BaseModel):
    position: int
    team: str
    points: int
    played: int
    goal_difference: int


class RankedMatch(BaseModel):
    match: Match
    excitement_score: int
    category: str
    reasoning: str


# Used only for LLM structured output — references matches by home/away team name
# so we can join back to the original Match objects (avoiding LLM date hallucination)
class LLMMatchRanking(BaseModel):
    home_team: str
    away_team: str
    competition: str
    excitement_score: int
    category: str
    reasoning: str


class LLMRankedMatchList(BaseModel):
    matches: list[LLMMatchRanking]
