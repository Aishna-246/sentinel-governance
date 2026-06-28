import json
import os
from datetime import datetime

from dotenv import load_dotenv
from rich.console import Console
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from sentinel.engine.base_policy import PolicyResult
from sentinel.engine.dpdp_policy import DPDPPolicy
from sentinel.engine.gdpr_policy import GDPRPolicy
from sentinel.engine.scoring import GovernanceScorer
from sentinel.lineage.graph_builder import LineageGraphBuilder
from sentinel.registry.base_connector import RegistryConnector
from sentinel.scanner.hybrid_scanner import HybridPIIScanner

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///sentinel.db")


class ComplianceEngine:
    FRAMEWORKS = {
        "dpdp": DPDPPolicy,
        "gdpr": GDPRPolicy,
    }

    def __init__(self, registry_connector: RegistryConnector, framework: str = "dpdp"):
        self.connector = registry_connector
        self.scanner = HybridPIIScanner()
        self.lineage_builder = LineageGraphBuilder()
        self.scorer = GovernanceScorer()
        self.framework = framework
        self.policy = self.FRAMEWORKS[framework]()
        self.engine = create_engine(DATABASE_URL)
        self.SessionLocal = sessionmaker(bind=self.engine)
        self.console = Console()

    def compile(self) -> dict:
        try:
            model_cards = self.connector.crawl_all()
        except ConnectionError:
            model_cards = []
            self.console.print("[yellow]Registry connection failed; using empty model card list.[/yellow]")

        pii_results = {}
        for model_card in model_cards:
            model_name = model_card.get("model_name", "")
            dataset = model_card.get("training_dataset", "")
            if dataset and os.path.exists(dataset):
                pii_results[model_name] = self.scanner.scan_csv(dataset)
            else:
                pii_results[model_name] = []

        egress_summary = self._read_egress_summary()
        decision_summary = self._read_decision_summary()
        lineage_graph = self.lineage_builder.build_graph(model_cards)

        return {
            "model_cards": model_cards,
            "pii_results": pii_results,
            "egress_summary": egress_summary,
            "decision_summary": decision_summary,
            "lineage_graph": lineage_graph,
            "compiled_at": datetime.utcnow().isoformat(),
        }

    def evaluate(self) -> dict:
        report_data = self.compile()
        governance_result = self.scorer.compute(report_data)

        try:
            policy_result = self.policy.evaluate(report_data)
        except NotImplementedError as exc:
            policy_result = None
            self.console.print(f"[yellow]Policy framework not implemented: {exc}[/yellow]")

        return {
            "report_data": report_data,
            "governance_score": governance_result.as_dict(),
            "policy_result": policy_result.as_dict() if policy_result else None,
            "framework": self.framework,
            "generated_at": datetime.utcnow().isoformat(),
        }

    def save_report(self, output_path: str = "output/report.json") -> dict:
        result = self.evaluate()
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as output_file:
            json.dump(result, output_file, indent=2, default=str)
        print(f"Report saved to {output_path}")
        return result

    def _read_egress_summary(self) -> dict:
        with self.engine.connect() as connection:
            try:
                result = connection.execute(
                    text(
                        "SELECT COUNT(*) as total, "
                        "SUM(CASE WHEN pii_detected=1 THEN 1 ELSE 0 END) as pii_count "
                        "FROM egress_logs"
                    )
                ).fetchone()
                total = int(result[0] or 0)
                pii_count = int(result[1] or 0)
                return {"total_calls": total, "pii_detected_count": pii_count}
            except Exception:
                return {"total_calls": 0, "pii_detected_count": 0}

    def _read_decision_summary(self) -> dict:
        with self.engine.connect() as connection:
            try:
                result = connection.execute(
                    text(
                        "SELECT COUNT(*) as total, "
                        "SUM(CASE WHEN human_reviewed=1 THEN 1 ELSE 0 END) as reviewed "
                        "FROM decision_logs"
                    )
                ).fetchone()
                total = int(result[0] or 0)
                reviewed = int(result[1] or 0)
                return {
                    "total": total,
                    "reviewed": reviewed,
                    "unreviewed": total - reviewed,
                    "review_rate": reviewed / total * 100 if total > 0 else 0,
                }
            except Exception:
                return {"total": 0, "reviewed": 0, "unreviewed": 0, "review_rate": 0}


if __name__ == "__main__":
    from sentinel.registry.mlflow_connector import MLflowConnector

    connector = MLflowConnector("http://localhost:5000")
    engine = ComplianceEngine(connector, framework="dpdp")

    print("Running Sentinel compliance evaluation...")
    result = engine.save_report("output/report.json")

    score = result["governance_score"]
    print(f"\nGovernance Score: {score['total_score']}/100 (Grade {score['grade']})")

    if result["policy_result"]:
        pr = result["policy_result"]
        print(f"DPDP Score: {pr['score']}/{pr['max_score']} ({pr['percentage']:.1f}%)")
        print(f"DPDP Grade: {pr['grade']}")
