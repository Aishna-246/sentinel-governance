import hashlib
import json
import os
import time
from datetime import datetime
from functools import wraps
from typing import Optional

from dotenv import load_dotenv
from fastapi import APIRouter, HTTPException, Request
from sqlalchemy import Boolean, Column, DateTime, Float, Integer, String, create_engine, desc, func
from sqlalchemy.orm import declarative_base, sessionmaker

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///sentinel.db")

Base = declarative_base()
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {})
SessionLocal = sessionmaker(bind=engine)


class DecisionLog(Base):
    __tablename__ = "decision_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    model_name = Column(String, nullable=False)
    model_version = Column(String, nullable=False)
    input_hash = Column(String, nullable=False)
    output_label = Column(String, nullable=False)
    output_score = Column(Float, nullable=False)
    latency_ms = Column(Float, nullable=False)
    human_reviewed = Column(Boolean, default=False)
    reviewed_at = Column(DateTime, nullable=True)
    reviewed_by = Column(String, nullable=True)


Base.metadata.create_all(engine)

audit_router = APIRouter(prefix="/audit", tags=["audit"])


def get_db_session():
    return SessionLocal()


def compute_input_hash(input_dict: dict) -> str:
    normalized = json.dumps(input_dict, sort_keys=True)
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def audit_decision(model_name: str, model_version: str):
    def decorator(func):
        @wraps(func)
        def wrapper(input_dict: dict, *args, **kwargs):
            start_time = time.time()
            input_hash = compute_input_hash(input_dict)
            result = func(input_dict, *args, **kwargs)
            latency_ms = (time.time() - start_time) * 1000.0

            if not isinstance(result, tuple) or len(result) != 2:
                raise ValueError("Audited function must return a tuple of (label, score)")

            output_label, output_score = result
            db = get_db_session()
            try:
                decision_log = DecisionLog(
                    model_name=model_name,
                    model_version=model_version,
                    input_hash=input_hash,
                    output_label=str(output_label),
                    output_score=float(output_score),
                    latency_ms=float(latency_ms),
                    human_reviewed=False,
                )
                db.add(decision_log)
                db.commit()
            except Exception:
                db.rollback()
                raise
            finally:
                db.close()

            return result

        return wrapper

    return decorator


def serialize_decision(entry: DecisionLog) -> dict:
    return {
        "id": entry.id,
        "timestamp": entry.timestamp.isoformat() if entry.timestamp else None,
        "model_name": entry.model_name,
        "model_version": entry.model_version,
        "input_hash": entry.input_hash,
        "output_label": entry.output_label,
        "output_score": entry.output_score,
        "latency_ms": entry.latency_ms,
        "human_reviewed": entry.human_reviewed,
        "reviewed_at": entry.reviewed_at.isoformat() if entry.reviewed_at else None,
        "reviewed_by": entry.reviewed_by,
    }


@audit_router.get("/decisions")
async def get_decisions(reviewed: Optional[bool] = None, since: Optional[str] = None) -> list[dict]:
    db = get_db_session()
    try:
        query = db.query(DecisionLog)

        if reviewed is not None:
            query = query.filter(DecisionLog.human_reviewed.is_(reviewed))

        if since:
            try:
                since_dt = datetime.fromisoformat(since)
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid since date format. Use ISO format.")
            query = query.filter(DecisionLog.timestamp >= since_dt)

        entries = query.order_by(desc(DecisionLog.timestamp)).limit(100).all()
        return [serialize_decision(entry) for entry in entries]
    finally:
        db.close()


@audit_router.patch("/decisions/{decision_id}/review")
async def review_decision(decision_id: int, request: Request) -> dict:
    payload = await request.json()
    reviewed_by = payload.get("reviewed_by")
    if not reviewed_by or not isinstance(reviewed_by, str):
        raise HTTPException(status_code=400, detail="reviewed_by is required and must be a string")

    db = get_db_session()
    try:
        decision_entry = db.query(DecisionLog).filter(DecisionLog.id == decision_id).first()
        if not decision_entry:
            raise HTTPException(status_code=404, detail="Decision log not found")

        decision_entry.human_reviewed = True
        decision_entry.reviewed_at = datetime.utcnow()
        decision_entry.reviewed_by = reviewed_by
        db.add(decision_entry)
        db.commit()
        db.refresh(decision_entry)
        return serialize_decision(decision_entry)
    finally:
        db.close()


@audit_router.get("/summary")
async def get_audit_summary() -> dict:
    db = get_db_session()
    try:
        total = db.query(func.count(DecisionLog.id)).scalar() or 0
        reviewed = db.query(func.count(DecisionLog.id)).filter(DecisionLog.human_reviewed.is_(True)).scalar() or 0
        unreviewed = db.query(func.count(DecisionLog.id)).filter(DecisionLog.human_reviewed.is_(False)).scalar() or 0
        model_rows = db.query(DecisionLog.model_name).distinct().all()
        models = [row[0] for row in model_rows]
        review_rate = (reviewed / total * 100.0) if total else 0.0

        return {
            "total": total,
            "reviewed": reviewed,
            "unreviewed": unreviewed,
            "review_rate": review_rate,
            "models": models,
        }
    finally:
        db.close()
