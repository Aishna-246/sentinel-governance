from datetime import datetime
import hashlib
import json
import os

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
import httpx
from sqlalchemy import Boolean, Column, DateTime, Float, Integer, String, create_engine, desc, func
from sqlalchemy.orm import declarative_base, sessionmaker

from sentinel.scanner.hybrid_scanner import HybridPIIScanner

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///sentinel.db")
PROVIDER_URL = os.getenv("PROVIDER_URL", "https://api.groq.com")
REAL_API_KEY = os.getenv("REAL_API_KEY", "")

Base = declarative_base()
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {})
SessionLocal = sessionmaker(bind=engine)


class EgressLog(Base):
    __tablename__ = "egress_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    provider = Column(String, nullable=False)
    model_called = Column(String, nullable=False)
    pii_detected = Column(Boolean, default=False)
    entity_types_found = Column(String, default="")
    message_count = Column(Integer, default=0)
    was_blocked = Column(Boolean, default=False)
    request_hash = Column(String, nullable=False)


scanner = HybridPIIScanner()
app = FastAPI(title="Sentinel LLM Egress Proxy")


@app.on_event("startup")
async def startup_event() -> None:
    Base.metadata.create_all(engine)
    print("Sentinel Egress Proxy running on port 8080")
    print(f"Forwarding to: {PROVIDER_URL}")
    print("PII scanning: ENABLED")


def get_db_session():
    return SessionLocal()


def compute_request_hash(body: dict) -> str:
    normalized = json.dumps(body, sort_keys=True)
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def build_response_from_httpx(response: httpx.Response) -> JSONResponse:
    try:
        content = response.json()
    except ValueError:
        content = {"detail": response.text}
    return JSONResponse(status_code=response.status_code, content=content)


@app.post("/v1/chat/completions")
async def proxy_chat_completions(request: Request) -> JSONResponse:
    try:
        body = await request.json()
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Request body must be valid JSON")

    messages = body.get("messages", []) or []
    aggregated_entity_types = []
    pii_detected = False

    for message in messages:
        content = None
        if isinstance(message, dict):
            if "content" in message and isinstance(message["content"], str):
                content = message["content"]
            elif isinstance(message.get("message"), str):
                content = message["message"]
        elif isinstance(message, str):
            content = message

        if not content:
            continue

        scan = scanner.scan_text(content)
        pii_detected = pii_detected or bool(scan.get("pii_detected", False))
        aggregated_entity_types.extend(scan.get("entity_types", []))

    provider_url = request.headers.get("X-Provider-URL") or PROVIDER_URL
    model_called = body.get("model", "unknown")
    message_count = len(messages)
    request_hash = compute_request_hash(body)
    entity_types_found = ",".join(aggregated_entity_types)

    db = get_db_session()
    try:
        log_entry = EgressLog(
            provider=provider_url,
            model_called=model_called,
            pii_detected=pii_detected,
            entity_types_found=entity_types_found,
            message_count=message_count,
            was_blocked=False,
            request_hash=request_hash,
        )
        db.add(log_entry)
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

    forwarded_headers = {
        key: value
        for key, value in request.headers.items()
        if key.lower() != "host"
    }
    forwarded_headers["Authorization"] = f"Bearer {REAL_API_KEY}"

    target_url = f"{provider_url.rstrip('/')}/v1/chat/completions"

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(target_url, json=body, headers=forwarded_headers, timeout=30.0)
        except httpx.RequestError as exc:
            return JSONResponse(
                status_code=502,
                content={
                    "detail": "Egress provider request failed",
                    "error": str(exc),
                },
            )

    return build_response_from_httpx(response)


@app.get("/proxy/logs")
async def get_proxy_logs() -> list[dict]:
    db = get_db_session()
    try:
        entries = (
            db.query(EgressLog)
            .order_by(EgressLog.timestamp.desc())
            .limit(50)
            .all()
        )
        return [
            {
                "id": entry.id,
                "timestamp": entry.timestamp.isoformat(),
                "provider": entry.provider,
                "model_called": entry.model_called,
                "pii_detected": entry.pii_detected,
                "entity_types_found": entry.entity_types_found,
                "message_count": entry.message_count,
                "was_blocked": entry.was_blocked,
                "request_hash": entry.request_hash,
            }
            for entry in entries
        ]
    finally:
        db.close()


@app.get("/proxy/summary")
async def get_proxy_summary() -> dict:
    db = get_db_session()
    try:
        total_calls = db.query(func.count(EgressLog.id)).scalar() or 0
        pii_detected_count = db.query(func.count(EgressLog.id)).filter(EgressLog.pii_detected.is_(True)).scalar() or 0
        clean_calls = db.query(func.count(EgressLog.id)).filter(EgressLog.pii_detected.is_(False)).scalar() or 0

        provider_counts = (
            db.query(EgressLog.provider, func.count(EgressLog.id).label("count"))
            .group_by(EgressLog.provider)
            .order_by(desc(func.count(EgressLog.id)))
            .limit(3)
            .all()
        )

        top_providers = [
            {"provider": provider, "count": count}
            for provider, count in provider_counts
        ]

        return {
            "total_calls": total_calls,
            "pii_detected_count": pii_detected_count,
            "clean_calls": clean_calls,
            "top_providers": top_providers,
        }
    finally:
        db.close()
