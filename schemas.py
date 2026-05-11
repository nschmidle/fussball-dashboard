from pydantic import BaseModel


class LeagueOut(BaseModel):
    league_shortcut: str
    league_name: str
    season: int
    total: int
    finished: int
    has_upcoming: bool


class MatchOut(BaseModel):
    id: int
    match_id: int
    league_shortcut: str
    league_name: str
    season: int
    matchday: str
    date: str
    team1: str
    team2: str
    score1: int | None
    score2: int | None
    finished: bool
    goal_count: int = 0


class StandingRow(BaseModel):
    pos: int
    team: str
    played: int
    wins: int
    draws: int
    losses: int
    goals_for: int
    goals_against: int
    gd: int
    points: int
