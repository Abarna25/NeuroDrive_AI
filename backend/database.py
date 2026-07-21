"""SQLite persistence for alert events and driving sessions (SQLAlchemy 2.0)."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, Float, Integer, String, create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

DATABASE_URL = "sqlite:///driveguard.db"

# check_same_thread=False: rows are written from the capture thread while
# FastAPI request handlers read from the event loop's threadpool.
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
Base = declarative_base()


class AlertEvent(Base):
    __tablename__ = "alert_events"

    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(String, nullable=False)
    alert_type = Column(String, nullable=False)
    risk_score = Column(Float, nullable=False)
    drowsiness_score = Column(Float, nullable=False)
    aggression_score = Column(Float, nullable=False)
    emotion_score = Column(Float, nullable=False)
    dominant_emotion = Column(String, nullable=False)
    ear_value = Column(Float, nullable=False)
    session_id = Column(String, nullable=False)

    def to_dict(self):
        return {
            "id": self.id,
            "timestamp": self.timestamp,
            "alert_type": self.alert_type,
            "risk_score": self.risk_score,
            "drowsiness_score": self.drowsiness_score,
            "aggression_score": self.aggression_score,
            "emotion_score": self.emotion_score,
            "dominant_emotion": self.dominant_emotion,
            "ear_value": self.ear_value,
            "session_id": self.session_id,
        }


class DriveSession(Base):
    __tablename__ = "sessions"

    id = Column(String, primary_key=True)
    start_time = Column(String, nullable=False)
    end_time = Column(String, nullable=True)
    total_alerts = Column(Integer, default=0)
    avg_risk_score = Column(Float, default=0.0)
    peak_risk_score = Column(Float, default=0.0)
    dominant_emotion = Column(String, default="neutral")

    def to_dict(self):
        return {
            "id": self.id,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "total_alerts": self.total_alerts,
            "avg_risk_score": self.avg_risk_score,
            "peak_risk_score": self.peak_risk_score,
            "dominant_emotion": self.dominant_emotion,
        }


def init_db():
    Base.metadata.create_all(bind=engine)


def start_session():
    session_id = str(uuid.uuid4())
    with SessionLocal() as db:
        db.add(
            DriveSession(
                id=session_id,
                start_time=datetime.now(timezone.utc).isoformat(),
            )
        )
        db.commit()
    return session_id


def end_session(session_id, summary_stats):
    with SessionLocal() as db:
        row = db.get(DriveSession, session_id)
        if row is None:
            return None
        row.end_time = datetime.now(timezone.utc).isoformat()
        row.total_alerts = summary_stats.get("total_alerts", 0)
        row.avg_risk_score = summary_stats.get("avg_risk_score", 0.0)
        row.peak_risk_score = summary_stats.get("peak_risk_score", 0.0)
        row.dominant_emotion = summary_stats.get("dominant_emotion", "neutral")
        db.commit()
        return row.to_dict()


def log_alert(session_id, risk_result, module_scores):
    with SessionLocal() as db:
        db.add(
            AlertEvent(
                timestamp=risk_result["timestamp"],
                alert_type=risk_result["status"],
                risk_score=risk_result["risk_score"],
                drowsiness_score=module_scores.get("drowsiness_score", 0.0),
                aggression_score=module_scores.get("aggression_score", 0.0),
                emotion_score=module_scores.get("emotion_score", 0.0),
                dominant_emotion=module_scores.get("dominant_emotion", "neutral"),
                ear_value=module_scores.get("ear_value", 0.0),
                session_id=session_id,
            )
        )
        db.commit()


def get_session_alerts(session_id):
    with SessionLocal() as db:
        rows = (
            db.query(AlertEvent)
            .filter(AlertEvent.session_id == session_id)
            .order_by(AlertEvent.id.asc())
            .all()
        )
        return [row.to_dict() for row in rows]


def get_session(session_id):
    with SessionLocal() as db:
        row = db.get(DriveSession, session_id)
        return row.to_dict() if row else None
