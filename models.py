from sqlalchemy import Column, Integer, Text, ForeignKey
from database import Base


class Match(Base):
    __tablename__ = "matches"

    id = Column(Integer, primary_key=True, autoincrement=True)
    match_id = Column(Integer, unique=True)
    league_shortcut = Column(Text)
    league_name = Column(Text)
    season = Column(Integer)
    matchday = Column(Text)
    date = Column(Text)
    team1 = Column(Text)
    team2 = Column(Text)
    score1 = Column(Integer, nullable=True)
    score2 = Column(Integer, nullable=True)
    finished = Column(Integer, default=0)


class Goal(Base):
    __tablename__ = "goals"

    id = Column(Integer, primary_key=True, autoincrement=True)
    goal_id = Column(Integer, unique=True)
    match_id = Column(Integer, ForeignKey("matches.match_id"))
    scorer = Column(Text)
    minute = Column(Integer)
    score1 = Column(Integer)
    score2 = Column(Integer)


class PushSubscription(Base):
    __tablename__ = "push_subscriptions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    endpoint = Column(Text, unique=True)
    p256dh = Column(Text)
    auth = Column(Text)
