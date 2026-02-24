"""
Pydantic models for hallucination detection reports.
Stored under analysis_data.meta.hallucination in the JSONB column.
"""
from pydantic import BaseModel, Field
from typing import List, Optional, Literal, Dict, Any

Severity = Literal["info", "warning", "error"]
Category = Literal["evidence", "rationale", "summary", "next_steps", "red_flags", "general"]


class EvidenceHit(BaseModel):
    """A match found in the input data for a given claim."""
    source: Literal["structured", "narrative", "document"]
    path: Optional[str] = None  # e.g., "abnormal_labs[5].value"
    snippet: str
    score: float


class Finding(BaseModel):
    """A single hallucination finding — one ungrounded or suspicious claim."""
    category: Category
    severity: Severity
    claim: str
    reason: str
    hits: List[EvidenceHit] = Field(default_factory=list)


class HallucinationReport(BaseModel):
    """Full report from the hallucination detector."""
    ok: bool
    score: float  # 0..1 groundedness score
    findings: List[Finding] = Field(default_factory=list)
    stats: Dict[str, Any] = Field(default_factory=dict)
