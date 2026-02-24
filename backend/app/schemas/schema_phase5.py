"""
Phase 5A Pydantic schemas:
  - RareCandidate / RareSpotlight  (rare disease spotlight)
  - CostLineItem / CostEstimate    (cost transparency)
"""
from pydantic import BaseModel, Field
from typing import List, Optional, Literal

Likelihood = Literal["high", "medium", "low"]


# ── Rare Disease Spotlight ───────────────────────────────────────

class RareCandidate(BaseModel):
    name: str
    likelihood: Likelihood = "low"
    why_this_fits: List[str] = Field(default_factory=list)
    supporting_evidence: List[str] = Field(default_factory=list)
    missing_evidence: List[str] = Field(default_factory=list)
    confirmatory_tests: List[str] = Field(default_factory=list)
    specialist_referral: Optional[str] = None
    safety_notes: List[str] = Field(default_factory=list)


class RareSpotlight(BaseModel):
    focus: str = "rare_disease_spotlight"
    candidates: List[RareCandidate] = Field(default_factory=list)
    diagnostic_delay_risk: int = Field(default=0, ge=0, le=100)
    delay_reasoning: List[str] = Field(default_factory=list)
    next_best_actions: List[str] = Field(default_factory=list)


# ── Cost Estimate ────────────────────────────────────────────────

class CostLineItem(BaseModel):
    item: str
    cpt_or_code: Optional[str] = None
    low: float = 0.0
    high: float = 0.0
    currency: str = "USD"
    notes: Optional[str] = None


class CostEstimate(BaseModel):
    focus: str = "cost_estimate"
    region: str = "US_cash_estimate"
    low_total: float = 0.0
    high_total: float = 0.0
    line_items: List[CostLineItem] = Field(default_factory=list)
    assumptions: List[str] = Field(default_factory=list)
    exclusions: List[str] = Field(default_factory=list)
    confidence: Likelihood = "medium"
