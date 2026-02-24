"""
Phase 6 — Trust Report Pydantic schemas.

Defines the structured output for evidence grounding, uncertainty scoring,
safety flags, and per-diagnosis trust assessment.
"""
from pydantic import BaseModel, Field
from typing import List, Optional, Literal

Level = Literal["ok", "warn", "fail"]
Confidence = Literal["high", "medium", "low"]


class EvidenceLink(BaseModel):
    """Links a single claim to its source in the case data."""
    claim: str
    supported: bool
    source_path: Optional[str] = None
    source_excerpt: Optional[str] = None
    reason: Optional[str] = None


class DiagnosisTrust(BaseModel):
    """Trust assessment for a single differential diagnosis."""
    diagnosis: str
    evidence_links: List[EvidenceLink] = Field(default_factory=list)
    support_ratio: float = 0.0
    confidence_score: int = 0
    confidence_level: Confidence = "low"
    uncertainty_reasons: List[str] = Field(default_factory=list)


class SafetyFlag(BaseModel):
    """A deterministic safety flag triggered by case data."""
    flag: str
    severity: Literal["low", "medium", "high", "critical"]
    triggered_by: List[str] = Field(default_factory=list)
    recommendation: str


class TrustReport(BaseModel):
    """Complete trust report for a case analysis."""
    status: Level
    overall_support_ratio: float = 0.0
    overall_confidence: int = 0
    safety_flags: List[SafetyFlag] = Field(default_factory=list)
    diagnoses: List[DiagnosisTrust] = Field(default_factory=list)
    global_warnings: List[str] = Field(default_factory=list)
    stats: dict = Field(default_factory=dict)
