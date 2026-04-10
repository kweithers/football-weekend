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


class RankedMatchList(BaseModel):
    matches: list[RankedMatch]
