"""Abstract base class for compliance policy frameworks.
To add GDPR support: create sentinel/engine/gdpr_policy.py implementing PolicyFramework.
To add EU AI Act: create sentinel/engine/eu_ai_act_policy.py implementing PolicyFramework.
Register new frameworks in ComplianceEngine.FRAMEWORKS dict.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional


@dataclass
class PolicyFinding:
    clause: str
    status: str
    detail: str
    recommendation: Optional[str] = None


@dataclass
class PolicyResult:
    framework_name: str
    score: float
    max_score: float
    findings: List[PolicyFinding] = field(default_factory=list)
    generated_at: datetime = field(default_factory=datetime.utcnow)
    percentage: float = field(init=False)
    grade: str = field(init=False)

    def __post_init__(self) -> None:
        self.percentage = (self.score / self.max_score * 100.0) if self.max_score else 0.0
        self.grade = self._determine_grade(self.percentage)

    def _determine_grade(self, percentage: float) -> str:
        if percentage >= 90.0:
            return "A"
        if percentage >= 75.0:
            return "B"
        if percentage >= 60.0:
            return "C"
        if percentage >= 40.0:
            return "D"
        return "F"

    def as_dict(self) -> dict:
        return {
            "framework_name": self.framework_name,
            "score": self.score,
            "max_score": self.max_score,
            "percentage": self.percentage,
            "grade": self.grade,
            "findings": [
                {
                    "clause": finding.clause,
                    "status": finding.status,
                    "detail": finding.detail,
                    "recommendation": finding.recommendation,
                }
                for finding in self.findings
            ],
            "generated_at": self.generated_at.isoformat(),
        }


class PolicyFramework(ABC):
    @property
    @abstractmethod
    def framework_name(self) -> str:
        pass

    @abstractmethod
    def get_clause_map(self) -> dict:
        pass

    @abstractmethod
    def evaluate(self, report_data: dict) -> PolicyResult:
        pass

    def _grade(self, percentage: float) -> str:
        if percentage >= 90.0:
            return "A"
        if percentage >= 75.0:
            return "B"
        if percentage >= 60.0:
            return "C"
        if percentage >= 40.0:
            return "D"
        return "F"
