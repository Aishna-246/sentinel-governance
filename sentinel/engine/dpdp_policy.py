import os
from sentinel.engine.base_policy import PolicyFramework, PolicyFinding, PolicyResult


class DPDPPolicy(PolicyFramework):
    @property
    def framework_name(self) -> str:
        return "DPDP Act 2023 / Rules 2025"

    def get_clause_map(self) -> dict:
        return {
            "model_inventory": "Rule 6, Clause 2(a) — Record of processing activities",
            "pii_scan_complete": "Rule 6, Clause 2(b) — Personal data categories documented",
            "vendor_data_flows": "Rule 6, Clause 2(c) — Third-party disclosures documented",
            "audit_log_present": "Rule 6, Clause 3 — Audit log retained for 1 year",
            "human_oversight": "Rule 13, Clause 4(b) — Human review of automated decisions",
            "algorithmic_audit": "Rule 13, Clause 4 — Algorithmic due-diligence",
        }

    def evaluate(self, report_data: dict) -> PolicyResult:
        clause_map = self.get_clause_map()
        findings: list[PolicyFinding] = []
        score = 0.0
        max_score = 6.0

        # Check 1 — model_inventory
        model_cards = report_data.get("model_cards")
        if isinstance(model_cards, list) and model_cards:
            findings.append(
                PolicyFinding(
                    clause=clause_map["model_inventory"],
                    status="pass",
                    detail=f"Model inventory present. {len(model_cards)} models registered and documented.",
                )
            )
            score += 1.0
        else:
            findings.append(
                PolicyFinding(
                    clause=clause_map["model_inventory"],
                    status="fail",
                    detail="No model inventory found. Register models in MLflow registry.",
                    recommendation="Run: sentinel crawl-registry",
                )
            )

        # Check 2 — pii_scan_complete
        pii_results = report_data.get("pii_results")
        if isinstance(pii_results, dict) and pii_results:
            findings.append(
                PolicyFinding(
                    clause=clause_map["pii_scan_complete"],
                    status="pass",
                    detail=f"PII scan complete for {len(pii_results)} models.",
                )
            )
            score += 1.0
        else:
            findings.append(
                PolicyFinding(
                    clause=clause_map["pii_scan_complete"],
                    status="fail",
                    detail="PII scan not run. Personal data columns not documented.",
                    recommendation="Run: sentinel scan-pii for each model dataset",
                )
            )

        # Check 3 — vendor_data_flows
        egress_summary = report_data.get("egress_summary", {}) or {}
        total_calls = int(egress_summary.get("total_calls", 0) or 0)
        pii_detected_count = int(egress_summary.get("pii_detected_count", 0) or 0)

        if total_calls == 0:
            findings.append(
                PolicyFinding(
                    clause=clause_map["vendor_data_flows"],
                    status="warn",
                    detail="No egress logs found. Vendor data flows not monitored.",
                    recommendation="Ensure data processing agreements with all LLM vendors.",
                )
            )
            score += 0.5
        elif pii_detected_count > 0:
            findings.append(
                PolicyFinding(
                    clause=clause_map["vendor_data_flows"],
                    status="warn",
                    detail=f"{pii_detected_count} outbound calls contained PII. Review vendor agreements.",
                    recommendation="Ensure data processing agreements with all LLM vendors.",
                )
            )
            score += 0.5
        else:
            findings.append(
                PolicyFinding(
                    clause=clause_map["vendor_data_flows"],
                    status="pass",
                    detail=f"Vendor flows monitored. {total_calls} calls logged, no PII detected.",
                )
            )
            score += 1.0

        # Check 4 — audit_log_present
        decision_summary = report_data.get("decision_summary", {}) or {}
        total_decisions = int(decision_summary.get("total", 0) or 0)

        if total_decisions > 0:
            findings.append(
                PolicyFinding(
                    clause=clause_map["audit_log_present"],
                    status="pass",
                    detail=f"Decision audit log active. {total_decisions} decisions logged.",
                )
            )
            score += 1.0
        else:
            findings.append(
                PolicyFinding(
                    clause=clause_map["audit_log_present"],
                    status="fail",
                    detail="No decision audit logs found.",
                    recommendation="Apply @audit_decision decorator to model inference functions.",
                )
            )

        # Check 5 — human_oversight
        reviewed = int(decision_summary.get("reviewed", 0) or 0)
        if total_decisions == 0:
            findings.append(
                PolicyFinding(
                    clause=clause_map["human_oversight"],
                    status="warn",
                    detail="No decisions logged. Cannot assess human oversight.",
                )
            )
            score += 0.5
        else:
            review_rate = reviewed / total_decisions * 100.0
            if review_rate >= 80.0:
                findings.append(
                    PolicyFinding(
                        clause=clause_map["human_oversight"],
                        status="pass",
                        detail=f"{review_rate:.1f}% of decisions reviewed by humans.",
                    )
                )
                score += 1.0
            elif review_rate >= 50.0:
                findings.append(
                    PolicyFinding(
                        clause=clause_map["human_oversight"],
                        status="warn",
                        detail=f"Only {review_rate:.1f}% of decisions reviewed. Target is 80%.",
                    )
                )
                score += 0.5
            else:
                findings.append(
                    PolicyFinding(
                        clause=clause_map["human_oversight"],
                        status="fail",
                        detail=f"Only {review_rate:.1f}% of decisions reviewed. Human oversight insufficient.",
                        recommendation="Use the dashboard to mark decisions as reviewed.",
                    )
                )

        # Check 6 — algorithmic_audit
        benchmark_path = os.path.join("docs", "benchmark_results.json")
        if os.path.exists(benchmark_path):
            findings.append(
                PolicyFinding(
                    clause=clause_map["algorithmic_audit"],
                    status="pass",
                    detail="Algorithmic audit complete. Benchmark results documented.",
                )
            )
            score += 1.0
        else:
            findings.append(
                PolicyFinding(
                    clause=clause_map["algorithmic_audit"],
                    status="warn",
                    detail="No benchmark results found. Algorithmic audit incomplete.",
                    recommendation="Run: python sentinel/scanner/benchmark.py",
                )
            )
            score += 0.5

        result = PolicyResult(
            framework_name=self.framework_name,
            score=score,
            max_score=max_score,
            findings=findings,
        )
        return result


if __name__ == "__main__":
    from rich.console import Console
    from rich.table import Table

    report_data = {
        "model_cards": [
            {"model_name": "credit_risk_model", "version": "1.0"},
            {"model_name": "fraud_detector", "version": "2.3"},
            {"model_name": "customer_churn", "version": "0.9"},
        ],
        "pii_results": {
            "credit_risk_model": {"pii_columns": ["aadhaar_no"]},
            "fraud_detector": {"pii_columns": ["pan_number"]},
        },
        "egress_summary": {"total_calls": 10, "pii_detected_count": 2},
        "decision_summary": {"total": 20, "reviewed": 15, "unreviewed": 5},
    }

    policy = DPDPPolicy()
    result = policy.evaluate(report_data)

    console = Console()
    console.print("[bold underline]DPDP Policy Evaluation[/]\n")
    console.print(f"Score: {result.score}/{result.max_score} ({result.percentage:.1f}%)")
    console.print(f"Grade: {result.grade}\n")

    table = Table(title="DPDP Policy Findings")
    table.add_column("Clause", style="cyan", no_wrap=True)
    table.add_column("Status", style="magenta")
    table.add_column("Detail", style="white")

    for finding in result.findings:
        color = "green" if finding.status == "pass" else "yellow" if finding.status == "warn" else "red"
        table.add_row(finding.clause, f"[{color}]{finding.status}[/{color}]", finding.detail)

    console.print(table)
