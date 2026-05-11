import asyncio
from datetime import datetime

import requests

from database import engine, Base
from models import Match, Goal
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

API_BASE = "https://api.openligadb.de"

LEAGUES = {
    "bl1": "1. Bundesliga",
    "bl2": "2. Bundesliga",
    "bl3": "3. Liga",
    "dfb": "DFB-Pokal",
    "ucl": "Champions League",
    "uel": "Europa League",
}


def _season():
    now = datetime.now()
    s = now.year
    if now.month < 7:
        s -= 1
    return s


async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def fetch_league(shortcut: str, season: int):
    url = f"{API_BASE}/getmatchdata/{shortcut}/{season}"
    resp = requests.get(url, timeout=10)
    if resp.status_code != 200:
        url = f"{API_BASE}/getmatchdata/{shortcut}"
        resp = requests.get(url, timeout=10)
    resp.raise_for_status()
    return resp.json()


async def store_league(session: AsyncSession, shortcut: str, name: str, season: int):
    data = await fetch_league(shortcut, season)
    for match in data:
        mid = match["matchID"]
        existing = await session.execute(select(Match).where(Match.match_id == mid))
        if existing.scalar():
            continue

        m = Match(
            match_id=mid,
            league_shortcut=shortcut,
            league_name=match.get("leagueName", name),
            season=season,
            matchday=match["group"]["groupName"],
            date=match["matchDateTime"],
            team1=match["team1"]["teamName"],
            team2=match["team2"]["teamName"],
            score1=None,
            score2=None,
            finished=1 if match["matchIsFinished"] else 0,
        )
        if match["matchResults"]:
            r = match["matchResults"][-1]
            m.score1 = r["pointsTeam1"]
            m.score2 = r["pointsTeam2"]

        session.add(m)
        await session.flush()

        for goal in match.get("goals", []):
            g = Goal(
                goal_id=goal["goalID"],
                match_id=mid,
                scorer=goal["goalGetterName"],
                minute=goal["matchMinute"],
                score1=goal["scoreTeam1"],
                score2=goal["scoreTeam2"],
            )
            session.add(g)

    await session.commit()
    return len(data)


async def run():
    await init_db()
    season = _season()
    total = 0
    print(f"Fetching season {season}/{season + 1}\n")
    async with AsyncSession(engine) as session:
        for sc, name in LEAGUES.items():
            print(f"  {name} ({sc})...", end=" ", flush=True)
            try:
                cnt = await store_league(session, sc, name, season)
                print(f"{cnt} matches")
                total += cnt
            except Exception as e:
                print(f"Error: {e}")
    print(f"\nDone. {total} matches")

if __name__ == "__main__":
    asyncio.run(run())
