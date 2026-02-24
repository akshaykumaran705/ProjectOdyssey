"""
Matching rules — deterministic, no ML dependencies.

- Token Jaccard overlap for text similarity
- Numeric anchoring for lab values / vitals
- Generic clinical advice detection
"""
from .normalize import extract_numbers


def token_jaccard(a: str, b: str) -> float:
    """Token-level Jaccard similarity between two normalized strings."""
    ta = set(a.split())
    tb = set(b.split())
    if not ta or not tb:
        return 0.0
    inter = len(ta & tb)
    union = len(ta | tb)
    return inter / union


def token_containment(claim: str, evidence: str) -> float:
    """
    What fraction of claim tokens appear in the evidence?
    More appropriate than Jaccard when evidence is much longer than claim.
    """
    claim_tokens = set(claim.split())
    evidence_tokens = set(evidence.split())
    if not claim_tokens:
        return 0.0
    return len(claim_tokens & evidence_tokens) / len(claim_tokens)


def numeric_compatible(claim: str, evidence: str) -> bool:
    """
    If the claim contains numbers (lab values, vitals),
    ALL those numbers must appear in the evidence.
    This catches fabricated labs like "Troponin 2.0" when real is "0.45".
    """
    nums = extract_numbers(claim)
    if not nums:
        return True  # no numbers to check
    ev_nums = set(extract_numbers(evidence))
    return all(n in ev_nums for n in nums)


def is_generic_advice(claim_norm: str) -> bool:
    """
    Returns True if a claim is generic clinical advice
    (not asserting patient-specific facts).
    """
    generic_markers = [
        "consider", "evaluate", "workup", "follow up", "screen", "assess",
        "obtain labs", "imaging", "cbc", "cmp", "urinalysis", "ecg",
        "monitor", "administer", "consult", "refer", "counseling",
        "reassess", "discharge", "admit", "observe", "repeat",
    ]
    return any(m in claim_norm for m in generic_markers)
