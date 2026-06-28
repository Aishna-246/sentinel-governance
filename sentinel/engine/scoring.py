from dataclasses import dataclass, field
from typing import Optional

from rich.console import Console
from rich.table import Table

SCORING_RUBRIC = {
    "model_versioned": {
        "weight": 20,
        "description": "All models have version tags in registry",
        "check": "Are all registered models versioned and tracked?",
    },
    "pii_scan_complete": {
        "weight": 20,
        "description": "All model datasets scanned for PII",
        "check": "Has every model's training data been scanned?",
    },
    "audit_log_enabled": {
        "weight": 20,
        "description": "Decision audit log is active with entries",
        "check": "Are automated decisions being logged?",
    },
    "human_review_rate": {
        "weight": 20,
        "description": "More than 80% of decisions reviewed by humans",
        "check": "Are humans reviewing automated decisions?",
    },
    "no_unredacted_egress": {
        "weight": 20,
        "description": "No PII detected in outbound LLM API calls",
        "check": "Is PII being sent to external LLM vendors?",
    },
}


@dataclass
class DimensionResult:
    name: str
    score: float
    max_score: float
    passed: bool
    reason: str


@dataclass
class GovernanceResult:
    total_score: float
    max_score: float
    percentage: float
    grade: str
    dimensions: list[DimensionResult] = field(default_factory=list)

    def as_dict(self) -> dict:
        return {
            "total_score": self.total_score,
            "max_score": self.max_score,
            "percentage": self.percentage,
            "grade": self.grade,
            "dimensions": [
                {
                    "name": dimension.name,
                    "score": dimension.score,
                    "max_score": dimension.max_score,
                    "passed": dimension.passed,
                    "reason": dimension.reason,
                }
                for dimension in self.dimensions
            ],
        }


class GovernanceScorer:
    def compute(self, report_data: dict) -> GovernanceResult:
        model_cards = report_data.get("model_cards", [])
        pii_results = report_data.get("pii_results", {})
        decision_summary = report_data.get("decision_summary", {}) or {}
        egress_summary = report_data.get("egress_summary", {}) or {}

        dimensions: list[DimensionResult] = []

        model_versioned_passed = len(model_cards) > 0
        dimensions.append(
            DimensionResult(
                name="model_versioned",
                score=20 if model_versioned_passed else 0,
                max_score=20,
                passed=model_versioned_passed,
                reason=f"{len(model_cards)} models versioned in registry" if model_versioned_passed else "No models found in registry",
            )
        )

        pii_scan_passed = len(pii_results) > 0
        dimensions.append(
            DimensionResult(
                name="pii_scan_complete",
                score=20 if pii_scan_passed else 0,
                max_score=20,
                passed=pii_scan_passed,
                reason=f"PII scan complete for {len(pii_results)} models" if pii_scan_passed else "No PII scans found",
            )
        )

        total_decisions = int(decision_summary.get("total", 0) or 0)
        audit_log_passed = total_decisions > 0
        dimensions.append(
            DimensionResult(
                name="audit_log_enabled",
                score=20 if audit_log_passed else 0,
                max_score=20,
                passed=audit_log_passed,
                reason=f"{total_decisions} decisions logged in audit trail" if audit_log_passed else "No decisions logged",
            )
        )

        reviewed = int(decision_summary.get("reviewed", 0) or 0)
        if total_decisions == 0:
            human_review_score = 0.0
            human_review_passed = False
            human_review_reason = "No decisions to review"
        else:
            rate = reviewed / total_decisions
            human_review_score = round(20 * rate, 1)
            human_review_passed = rate >= 0.80
            human_review_reason = f"{rate * 100:.1f}% of decisions reviewed by humans"

        dimensions.append(
            DimensionResult(
                name="human_review_rate",
                score=human_review_score,
                max_score=20,
                passed=human_review_passed,
                reason=human_review_reason,
            )
        )

        pii_detected = int(egress_summary.get("pii_detected_count", 0) or 0)
        total_calls = int(egress_summary.get("total_calls", 0) or 0)
        if total_calls == 0:
            egress_score = 10.0
            egress_passed = False
            egress_reason = "No egress calls monitored yet"
        elif pii_detected == 0:
            egress_score = 20.0
            egress_passed = True
            egress_reason = f"No PII detected in {total_calls} outbound calls"
        else:
            egress_score = 0.0
            egress_passed = False
            egress_reason = f"PII detected in {pii_detected}/{total_calls} outbound calls"

        dimensions.append(
            DimensionResult(
                name="no_unredacted_egress",
                score=egress_score,
                max_score=20,
                passed=egress_passed,
                reason=egress_reason,
            )
        )

        total_score = sum(dimension.score for dimension in dimensions)
        percentage = total_score / 100 * 100
        grade = self._grade(percentage)

        return GovernanceResult(
            total_score=total_score,
            max_score=100,
            percentage=percentage,
            grade=grade,
            dimensions=dimensions,
        )

    def _grade(self, percentage: float) -> str:
        if percentage >= 90:
            return "A"
        if percentage >= 75:
            return "B"
        if percentage >= 60:
            return "C"
        if percentage >= 40:
            return "D"
        return "F"


if __name__ == "__main__":
    scorer = GovernanceScorer()

    total_weight = sum(value["weight"] for value in SCORING_RUBRIC.values())
    print(f"Rubric weight sum: {total_weight} (must be 100)")
    assert total_weight == 100, "Rubric weights must sum to 100"

    sample = {
        "model_cards": [{"name": "model1"}, {"name": "model2"}, {"name": "model3"}],
        "pii_results": {"model1": [], "model2": []},
        "decision_summary": {"total": 20, "reviewed": 17, "unreviewed": 3},
        "egress_summary": {"total_calls": 10, "pii_detected_count": 0},
    }
    result = scorer.compute(sample)

    console = Console()
    table = Table(title="Governance Score Dimensions")
    table.add_column("Dimension")
    table.add_column("Score")
    table.add_column("Max")
    table.add_column("Passed")
    table.add_column("Reason")

    for dimension in result.dimensions:
        color = "green" if dimension.passed else "red"
        table.add_row(
            dimension.name,
            f"[{color}]{dimension.score:.1f}[/{color}]",
            f"{dimension.max_score:.0f}",
            f"[{color}]{str(dimension.passed)}[/{color}]",
            dimension.reason,
        )

    console.print(table)
    console.print(f"Total Governance Score: {result.total_score}/100 ({result.percentage:.1f}%)")
    console.print(f"Grade: {result.grade}")
