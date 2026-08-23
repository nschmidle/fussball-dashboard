import asyncio
import os
import time
from collections import deque
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests
from fastapi import FastAPI, Depends, Query, Request
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from pywebpush import webpush, WebPushException

from database import get_db, engine
from models import Match, Goal, PushSubscription
from schemas import LeagueOut, MatchOut, StandingRow, SpieltagGroup
from scraper import BERLIN, LEAGUES, scrape_all

SCRAPE_HOUR_UTC = int(os.environ.get("SCRAPE_HOUR_UTC", "6"))
LIVE_CACHE_TTL = int(os.environ.get("LIVE_CACHE_TTL", "300"))
LIVE_POLL_INTERVAL = int(os.environ.get("LIVE_POLL_INTERVAL", "120"))
MATCH_MAX_RUNTIME = timedelta(hours=3)
SLEEP_CHUNK = 3600
APP_VERSION = "0.5.2"

VAPID_PRIVATE = None
VAPID_PUBLIC = None
VAPID_CLAIMS = None

_scrape_lock = asyncio.Lock()
_scrape_history = deque(maxlen=20)


async def scrape_all_locked(trigger="manual"):
    async with _scrape_lock:
        t0 = time.monotonic()
        try:
            total, updated = await scrape_all()
        except Exception as e:
            _scrape_history.appendleft({
                "ts": _utcnow().isoformat(),
                "trigger": trigger,
                "duration_s": round(time.monotonic() - t0, 2),
                "error": str(e),
            })
            raise
        _scrape_history.appendleft({
            "ts": _utcnow().isoformat(),
            "trigger": trigger,
            "duration_s": round(time.monotonic() - t0, 2),
            "total": total,
            "updated": updated,
        })


def _utcnow():
    return datetime.now(timezone.utc)


async def _next_kickoff_utc():
    async with engine.connect() as conn:
        row = (
            await conn.execute(
                select(func.min(Match.date)).where(
                    Match.finished == 0, Match.date > _utcnow().isoformat()
                )
            )
        ).scalar()
    return datetime.fromisoformat(row) if row else None


async def _running_matches_exist():
    now = _utcnow()
    async with engine.connect() as conn:
        cnt = (
            await conn.execute(
                select(func.count())
                .select_from(Match)
                .where(
                    Match.finished == 0,
                    Match.date <= now.isoformat(),
                    Match.date > (now - MATCH_MAX_RUNTIME).isoformat(),
                )
            )
        ).scalar()
    return bool(cnt)


async def daily_scrape_loop():
    while True:
        now = _utcnow()
        target = now.replace(hour=SCRAPE_HOUR_UTC, minute=0, second=0, microsecond=0)
        if target <= now:
            target += timedelta(days=1)
        wait_s = (target - now).total_seconds()
        berlin = target.astimezone(BERLIN).strftime("%H:%M")
        print(f"[scheduler] next OpenLigaDB update: {target.isoformat()} (= {berlin} Europe/Berlin) ({int(wait_s)}s)")
        await asyncio.sleep(wait_s)
        try:
            print("[scheduler] running daily OpenLigaDB update...")
            await scrape_all_locked("daily")
        except Exception as e:
            print(f"[scheduler] daily update failed: {e}")


async def live_window_loop():
    while True:
        try:
            if await _running_matches_exist():
                kickoff = _utcnow()
                print(f"[live-window] matches already running, entering poll mode")
            else:
                kickoff = await _next_kickoff_utc()
                if kickoff is None:
                    await asyncio.sleep(SLEEP_CHUNK)
                    continue
                remaining = (kickoff - _utcnow()).total_seconds()
                print(f"[live-window] next match starts {kickoff.isoformat()} ({int(remaining)}s)")
                while True:
                    remaining = (kickoff - _utcnow()).total_seconds()
                    if remaining <= 0:
                        break
                    await asyncio.sleep(min(remaining, SLEEP_CHUNK))
        except asyncio.CancelledError:
            raise
        except Exception as e:
            print(f"[live-window] error: {e}")
            await asyncio.sleep(60)
            continue

        print("[live-window] poll mode active")
        while True:
            try:
                await scrape_all_locked("live")
            except Exception as e:
                print(f"[live-window] scrape failed: {e}")
            try:
                if not await _running_matches_exist():
                    break
            except asyncio.CancelledError:
                raise
            except Exception as e:
                print(f"[live-window] check failed: {e}")
            await asyncio.sleep(LIVE_POLL_INTERVAL)
        print("[live-window] no running matches anymore, window closed")


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Match.metadata.create_all)
    tasks = [
        asyncio.create_task(daily_scrape_loop()),
        asyncio.create_task(live_window_loop()),
    ]
    yield
    for t in tasks:
        t.cancel()
    for t in tasks:
        try:
            await t
        except asyncio.CancelledError:
            pass
    await engine.dispose()


app = FastAPI(title="Fußball Dashboard", version=APP_VERSION, lifespan=lifespan)


def init_vapid():
    global VAPID_PRIVATE, VAPID_PUBLIC, VAPID_CLAIMS
    from cryptography.fernet import Fernet
    from py_vapid import Vapid
    v = Vapid()
    try:
        v.load("vapid_keys.json")
    except Exception:
        v.generate_keys()
        v.save("vapid_keys.json")
    VAPID_PRIVATE = v.private_key
    VAPID_PUBLIC = v.public_key
    VAPID_CLAIMS = {"sub": "mailto:nschmidle@web.de"}


@app.on_event("startup")
async def startup():
    init_vapid()


@app.get("/api/push/vapid-key")
async def push_vapid_key():
    return {"public_key": VAPID_PUBLIC}


@app.post("/api/push/subscribe")
async def push_subscribe(request: Request, db: AsyncSession = Depends(get_db)):
    body = await request.json()
    sub = PushSubscription(
        endpoint=body["endpoint"],
        p256dh=body["keys"]["p256dh"],
        auth=body["keys"]["auth"],
    )
    existing = await db.execute(
        select(PushSubscription).where(PushSubscription.endpoint == body["endpoint"])
    )
    if not existing.scalar():
        db.add(sub)
        await db.commit()
    return {"ok": True}


@app.post("/api/push/test")
async def push_test(db: AsyncSession = Depends(get_db)):
    rows = await db.execute(select(PushSubscription))
    subs = rows.scalars().all()
    sent = 0
    for s in subs:
        try:
            webpush(
                subscription_info={"endpoint": s.endpoint, "keys": {"p256dh": s.p256dh, "auth": s.auth}},
                data='{"title":"⚽ Test","body":"Push funktioniert!"}',
                vapid_private_key=VAPID_PRIVATE,
                vapid_claims=VAPID_CLAIMS,
            )
            sent += 1
        except WebPushException:
            if s.endpoint:
                await db.delete(s)
                await db.commit()
    return {"sent": sent}


@app.get("/api/version")
async def get_version():
    return {"version": APP_VERSION, "build_date": os.environ.get("BUILD_DATE", "dev")}


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

_live_cache = {"data": None, "ts": 0.0}
_live_lock = asyncio.Lock()


async def _fetch_live():
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


@app.get("/api/live")
async def get_live():
    now = time.monotonic()
    if _live_cache["data"] is not None and now - _live_cache["ts"] < LIVE_CACHE_TTL:
        return _live_cache["data"]
    async with _live_lock:
        now = time.monotonic()
        if _live_cache["data"] is not None and now - _live_cache["ts"] < LIVE_CACHE_TTL:
            return _live_cache["data"]
        print("[live] fetching from OpenLigaDB...")
        data = await _fetch_live()
        _live_cache["data"] = data
        _live_cache["ts"] = time.monotonic()
        return data


@app.get("/api/spieltag", response_model=list[SpieltagGroup])
async def get_spieltag(db: AsyncSession = Depends(get_db)):
    # "Heute" als Kalendertag Europe/Berlin, Grenzen als UTC-ISO-Vergleich
    now_berlin = _utcnow().astimezone(BERLIN)
    start = now_berlin.replace(hour=0, minute=0, second=0, microsecond=0).astimezone(timezone.utc)
    end = start + timedelta(days=1)
    rows = (
        await db.execute(
            select(Match)
            .where(Match.date >= start.isoformat(), Match.date < end.isoformat())
            .order_by(Match.date)
        )
    ).scalars().all()

    by_league: dict[str, list[Match]] = {}
    for m in rows:
        by_league.setdefault(m.league_shortcut, []).append(m)

    groups = []
    for sc in LEAGUES:
        ms = by_league.get(sc, [])
        if not ms:
            continue
        groups.append(SpieltagGroup(
            league_shortcut=sc,
            league_name=ms[0].league_name or LEAGUES[sc],
            matches=[
                MatchOut(
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
                )
                for m in ms
            ],
        ))
    return groups


@app.get("/api/scrape-history")
async def get_scrape_history():
    return list(_scrape_history)


# Static frontend als Fallback (muss nach API-Routen sein)
frontend_dist = Path(__file__).parent / "frontend" / "dist"
if frontend_dist.exists():
    from fastapi.staticfiles import StaticFiles
    app.mount("/", StaticFiles(directory=str(frontend_dist), html=True), name="frontend")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server:app", host="0.0.0.0", port=8080, reload=True)
