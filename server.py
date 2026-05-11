import asyncio
from contextlib import asynccontextmanager
from pathlib import Path

import requests
from fastapi import FastAPI, Depends, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db, engine
from models import Match, Goal
from schemas import LeagueOut, MatchOut, StandingRow


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Match.metadata.create_all)
    yield
    await engine.dispose()


app = FastAPI(title="Fußball Dashboard", version="2.0.0", lifespan=lifespan)


@app.get("/api/leagues", response_model=list[LeagueOut])
async def get_leagues(db: AsyncSession = Depends(get_db)):
    rows = await db.execute(
        select(
            Match.league_shortcut,
            Match.league_name,
            Match.season,
            func.count(Match.id).label("total"),
            func.sum(Match.finished).label("finished"),
            func.max(~(Match.finished == 1)).label("has_upcoming"),
        )
        .group_by(Match.league_shortcut, Match.league_name, Match.season)
        .order_by(Match.season.desc(), Match.league_shortcut)
    )
    return [
        LeagueOut(
            league_shortcut=r.league_shortcut,
            league_name=r.league_name,
            season=r.season,
            total=r.total,
            finished=r.finished or 0,
            has_upcoming=bool(r.has_upcoming),
        )
        for r in rows
    ]


@app.get("/api/matchdays")
async def get_matchdays(league: str = "bl1", db: AsyncSession = Depends(get_db)):
    rows = await db.execute(
        select(Match.matchday)
        .where(Match.league_shortcut == league)
        .distinct()
        .order_by(Match.matchday)
    )
    return [r[0] for r in rows]


@app.get("/api/matches", response_model=list[MatchOut])
async def get_matches(
    league: str = Query("bl1"),
    season: int | None = None,
    matchday: str | None = None,
    team: str | None = None,
    limit: int = Query(50, le=500),
    db: AsyncSession = Depends(get_db),
):
    q = select(Match).where(Match.league_shortcut == league)
    if season:
        q = q.where(Match.season == season)
    if matchday:
        q = q.where(Match.matchday == matchday)
    if team:
        q = q.where((Match.team1.ilike(f"%{team}%")) | (Match.team2.ilike(f"%{team}%")))
    q = q.order_by(Match.date.desc()).limit(limit)
    rows = await db.execute(q)
    matches = rows.scalars().all()

    result = []
    for m in matches:
        gcount = await db.execute(
            select(func.count(Goal.id)).where(Goal.match_id == m.match_id)
        )
        result.append(MatchOut(
            id=m.id,
            match_id=m.match_id,
            league_shortcut=m.league_shortcut,
            league_name=m.league_name,
            season=m.season,
            matchday=m.matchday,
            date=m.date,
            team1=m.team1,
            team2=m.team2,
            score1=m.score1,
            score2=m.score2,
            finished=bool(m.finished),
            goal_count=gcount.scalar() or 0,
        ))
    return result


@app.get("/api/standings", response_model=list[StandingRow])
async def get_standings(league: str = "bl1", db: AsyncSession = Depends(get_db)):
    rows = await db.execute(
        select(Match).where(Match.league_shortcut == league, Match.finished == 1)
    )
    matches = rows.scalars().all()

    teams: dict[str, dict] = {}
    for m in matches:
        if m.score1 is None:
            continue
        for t, gf, ga in [(m.team1, m.score1, m.score2), (m.team2, m.score2, m.score1)]:
            if t not in teams:
                teams[t] = {"team": t, "played": 0, "wins": 0, "draws": 0,
                            "losses": 0, "goals_for": 0, "goals_against": 0, "points": 0}
            teams[t]["played"] += 1
            teams[t]["goals_for"] += gf
            teams[t]["goals_against"] += ga
            if gf > ga:
                teams[t]["wins"] += 1
                teams[t]["points"] += 3
            elif gf == ga:
                teams[t]["draws"] += 1
                teams[t]["points"] += 1
            else:
                teams[t]["losses"] += 1

    sorted_teams = sorted(teams.values(), key=lambda x: (-x["points"], -(x["goals_for"] - x["goals_against"])))
    return [
        StandingRow(pos=i, gd=t["goals_for"] - t["goals_against"], **t)
        for i, t in enumerate(sorted_teams, 1)
    ]


@app.get("/api/stats")
async def get_stats(league: str = "bl1", db: AsyncSession = Depends(get_db)):
    base = [Match.league_shortcut == league, Match.finished == 1, Match.score1.isnot(None)]

    goals_per_md = await db.execute(
        select(Match.matchday, (func.sum(Match.score1) + func.sum(Match.score2)).label("goals"), func.count().label("matches"))
        .where(*base)
        .group_by(Match.matchday)
        .order_by(Match.matchday)
    )
    gpm = [{"matchday": r.matchday, "goals": r.goals, "matches": r.matches} for r in goals_per_md]

    dist = await db.execute(
        select(
            func.sum(Match.score1 > Match.score2).label("home_wins"),
            func.sum(Match.score1 == Match.score2).label("draws"),
            func.sum(Match.score1 < Match.score2).label("away_wins"),
            func.avg(Match.score1 + Match.score2).label("avg_goals"),
        ).where(*base)
    )
    d = dist.one()

    scorers = await db.execute(
        select(Goal.scorer, func.count().label("goals"))
        .join(Match, Match.match_id == Goal.match_id)
        .where(*base)
        .group_by(Goal.scorer)
        .order_by(func.count().desc())
        .limit(20)
    )

    return {
        "goals_per_matchday": gpm,
        "result_distribution": {
            "home_wins": d.home_wins or 0,
            "draws": d.draws or 0,
            "away_wins": d.away_wins or 0,
            "avg_goals": round(float(d.avg_goals or 0), 2),
        },
        "top_scorers": [{"scorer": r.scorer, "goals": r.goals} for r in scorers],
    }


LIVE_LEAGUES = {"bl1": "1. Bundesliga", "bl2": "2. Bundesliga", "dfb": "DFB-Pokal", "ucl": "Champions League", "uel": "Europa League"}


@app.get("/api/live")
async def get_live():
    results = []
    for shortcut, name in LIVE_LEAGUES.items():
        try:
            resp = await asyncio.to_thread(
                requests.get, f"https://api.openligadb.de/getmatchdata/{shortcut}", timeout=10
            )
            resp.raise_for_status()
            matches = resp.json()
        except Exception:
            continue

        for m in matches:
            goals = [
                {
                    "goal_id": g["goalID"],
                    "scorer": g["goalGetterName"],
                    "minute": g["matchMinute"],
                    "score1": g["scoreTeam1"],
                    "score2": g["scoreTeam2"],
                }
                for g in m.get("goals", [])
            ]
            results.append({
                "league": name,
                "league_shortcut": shortcut,
                "match_id": m["matchID"],
                "matchday": m["group"]["groupName"],
                "team1": m["team1"]["teamName"],
                "team2": m["team2"]["teamName"],
                "score1": m["matchResults"][-1]["pointsTeam1"] if m["matchResults"] else None,
                "score2": m["matchResults"][-1]["pointsTeam2"] if m["matchResults"] else None,
                "finished": m["matchIsFinished"],
                "goals": goals,
            })
    return results


# Static frontend als Fallback (muss nach API-Routen sein)
frontend_dist = Path(__file__).parent / "frontend" / "dist"
if frontend_dist.exists():
    from fastapi.staticfiles import StaticFiles
    app.mount("/", StaticFiles(directory=str(frontend_dist), html=True), name="frontend")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server:app", host="0.0.0.0", port=8080, reload=True)
