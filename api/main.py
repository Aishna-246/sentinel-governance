import io
import json
import os

import pandas as pd
from dotenv import load_dotenv
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from sentinel.audit.decision_logger import DecisionLog, SessionLocal, audit_router
from sentinel.engine.compliance_engine import ComplianceEngine
from sentinel.engine.scoring import GovernanceScorer, SCORING_RUBRIC
from sentinel.lineage.graph_builder import LineageGraphBuilder
from sentinel.proxy.egress_proxy import app as proxy_app
from sentinel.registry.mlflow_connector import MLflowConnector
from sentinel.scanner.hybrid_scanner import HybridPIIScanner

load_dotenv()
MLFLOW_URI = os.getenv("MLFLOW_URI", "http://localhost:5000")

app = FastAPI(
    title="Sentinel — AI Governance Platform",
    description="Automated AI governance, model inventory, PII detection, and compliance reporting.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(audit_router)
app.mount("/proxy", proxy_app)

connector = MLflowConnector(MLFLOW_URI)
scanner = HybridPIIScanner()
lineage_builder = LineageGraphBuilder()
scorer = GovernanceScorer()


@app.on_event("startup")
async def startup_event() -> None:
    print("Sentinel API started")
    print(f"MLflow: {MLFLOW_URI}")
    print("Docs: http://localhost:8000/docs")


@app.get("/")
async def root() -> dict:
    return {
        "status": "ok",
        "service": "sentinel-governance",
        "version": "1.0.0",
        "docs": "/docs",
    }


@app.get("/api/models")
async def get_models() -> list[dict]:
    try:
        return connector.crawl_all()
    except ConnectionError:
        return []


@app.get("/api/score")
async def get_score() -> dict:
    engine = ComplianceEngine(connector, framework="dpdp")
    result = engine.evaluate()
    return {
        "governance_score": result["governance_score"],
        "policy_result": result["policy_result"],
        "framework": "dpdp",
        "compiled_at": result["generated_at"],
    }


@app.get("/api/lineage/graph")
async def get_lineage_graph() -> dict:
    model_cards_path = os.path.join("docs", "model_cards.json")
    if os.path.exists(model_cards_path):
        with open(model_cards_path, "r", encoding="utf-8") as model_cards_file:
            model_cards = json.load(model_cards_file)
    else:
        try:
            model_cards = connector.crawl_all()
        except ConnectionError:
            model_cards = []

    return lineage_builder.build_graph(model_cards)


@app.post("/api/scan")
async def scan_upload(file: UploadFile = File(...)) -> dict:
    contents = await file.read()
    csv_buffer = io.StringIO(contents.decode("utf-8"))
    df = pd.read_csv(csv_buffer)
    scan_results = scanner.scan_dataframe(df)

    pii_count = sum(1 for result in scan_results if result.get("is_pii"))
    clean_count = len(scan_results) - pii_count

    return {
        "filename": file.filename,
        "total_columns": len(df.columns),
        "results": scan_results,
        "pii_count": pii_count,
        "clean_count": clean_count,
    }


@app.get("/api/report")
async def get_report() -> dict:
    engine = ComplianceEngine(connector, framework="dpdp")
    return engine.save_report("output/report.json")


@app.get("/api/config")
async def get_config() -> dict:
    return {
        "mlflow_uri": MLFLOW_URI,
        "framework": "dpdp",
        "scoring_rubric": SCORING_RUBRIC,
        "supported_frameworks": {
            "dpdp": {"status": "active", "name": "DPDP Act 2023 / Rules 2025"},
            "gdpr": {"status": "stub", "name": "GDPR (EU) 2016/679"},
            "eu_ai_act": {"status": "planned", "name": "EU AI Act 2024"},
        },
    }
