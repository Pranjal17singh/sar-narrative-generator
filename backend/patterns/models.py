"""Pattern detection result models."""

from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from enum import Enum


class PatternType(str, Enum):
    """Types of suspicious patterns."""
    FUNNEL = "funnel"
    RAPID_MOVEMENT = "rapid_movement"
    STRUCTURING = "structuring"
    CROSS_BORDER = "cross_border"
    ROUND_AMOUNTS = "round_amounts"
    VELOCITY_SPIKE = "velocity_spike"


class Severity(str, Enum):
    """Pattern severity levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class PatternMatch(BaseModel):
    """Result of pattern detection."""
    pattern_type: PatternType
    confidence: float = Field(ge=0.0, le=1.0)
    severity: Severity = Severity.MEDIUM
    description: str
    evidence: List[Dict[str, Any]] = []
    affected_transactions: List[str] = []
    recommendation: Optional[str] = None

    class Config:
        use_enum_values = True


class PatternSummary(BaseModel):
    """Summary of all detected patterns."""
    total_patterns: int
    high_severity_count: int
    patterns: List[PatternMatch]
    risk_score: float = Field(ge=0.0, le=100.0)
    risk_level: str  # Low, Medium, High, Critical


def calculate_risk_score(patterns: List[PatternMatch]) -> tuple[float, str]:
    """
    Calculate overall risk score based on detected patterns.

    Returns (score, level) tuple.
    """
    if not patterns:
        return 0.0, "Low"

    # Weight by severity
    severity_weights = {
        Severity.LOW: 10,
        Severity.MEDIUM: 25,
        Severity.HIGH: 40,
        Severity.CRITICAL: 60,
    }

    total_score = sum(
        severity_weights.get(Severity(p.severity), 25) * p.confidence
        for p in patterns
    )

    # Cap at 100
    score = min(total_score, 100.0)

    # Determine level
    if score >= 75:
        level = "Critical"
    elif score >= 50:
        level = "High"
    elif score >= 25:
        level = "Medium"
    else:
        level = "Low"

    return round(score, 1), level
