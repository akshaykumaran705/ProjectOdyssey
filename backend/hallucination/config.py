"""
Configuration knobs for the hallucination detector.
"""
from pydantic import BaseModel
from typing import Literal

Mode = Literal["off", "warn", "strict"]


class HallucinationConfig(BaseModel):
    mode: Mode = "warn"

    # Matching thresholds
    min_ngram_hit_score: float = 0.78     # token overlap / Jaccard score
    min_numeric_hit_score: float = 0.90   # numbers/labs should match strongly
    max_hits_per_claim: int = 3

    # What to scan besides support/against
    check_rationale: bool = True
    check_summary: bool = True
    check_next_steps: bool = True

    # Strict gating
    max_error_findings: int = 2           # in strict mode, fail if > this
    max_total_findings: int = 8           # also fail if too noisy

    # Limits (avoid token-bloat / slow matching)
    max_claim_chars: int = 240
    max_claims_total: int = 80

    # Safety: treat these as "allowed" generic advice claims
    allow_generic_clinical_advice: bool = True
