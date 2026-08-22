import asyncio
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

import requests

from database import engine, Base
from models import Match, Goal
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, bindparam

API_BASE = "https://api.openligadb.de"
BERLIN = ZoneInfo("Europe/Berlin")

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


def _to_utc(dt_str):
    dt = datetime.fromisoformat(dt_str)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=BERLIN)
    return dt.astimezone(timezone.utc).isoformat()


async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await _migrate_dates_to_utc(conn)


async def _migrate_dates_to_utc(conn):
    res = await conn.execute(select(Match.id, Match.date))
    updates = []
    for mid, d in res.all():
        try:
            dt = datetime.fromisoformat(d)
        except (TypeError, ValueError):
            continue
        if dt.tzinfo is None:
            utc = dt.replace(tzinfo=BERLIN).astimezone(timezone.utc).isoformat()
            updates.append({"mid": mid, "date": utc})
    if not updates:
        return 0
    await conn.execute(
        Match.__table__.update().where(Match.__table__.c.id == bindparam("mid")),
        updates,
    )
    print(f"[migrate] {len(updates)} match dates converted to UTC")
    return len(updates)


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
    updated = 0
    for match in data:
        mid = match["matchID"]
        match_date = _to_utc(match["matchDateTime"])
        existing = await session.execute(select(Match).where(Match.match_id == mid))
        m = existing.scalar()
        if m:
            before = (m.score1, m.score2, m.finished, m.date)
            m.date = match_date
            if match["matchResults"]:
                r = match["matchResults"][-1]
                m.score1 = r["pointsTeam1"]
                m.score2 = r["pointsTeam2"]
            m.finished = 1 if match["matchIsFinished"] else 0
            if (m.score1, m.score2, m.finished, m.date) != before:
                updated += 1
        else:
            m = Match(
                match_id=mid,
                league_shortcut=shortcut,
                league_name=match.get("leagueName", name),
                season=season,
                matchday=match["group"]["groupName"],
                date=match_date,
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

        goal_ids = set(
            (await session.execute(select(Goal.goal_id).where(Goal.match_id == mid))).scalars()
        )
        for goal in match.get("goals", []):
            if goal["goalID"] in goal_ids:
                continue
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
    return len(data), updated


async def scrape_all():
    await init_db()
    season = _season()
    total = 0
    total_updated = 0
    print(f"Fetching season {season}/{season + 1}\n")
    async with AsyncSession(engine) as session:
        for sc, name in LEAGUES.items():
            print(f"  {name} ({sc})...", end=" ", flush=True)
            try:
                cnt, updated = await store_league(session, sc, name, season)
                print(f"{cnt} matches, {updated} updated")
                total += cnt
                total_updated += updated
            except Exception as e:
                print(f"Error: {e}")
    print(f"\nDone. {total} matches, {total_updated} updated")
    return total, total_updated


async def run():
    await scrape_all()

if __name__ == "__main__":
    asyncio.run(run())
