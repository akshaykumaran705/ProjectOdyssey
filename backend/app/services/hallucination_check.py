"""
Evidence Grounding Validator — the core trust layer.

Verifies that EVERY evidence claim the LLM produces actually exists
in the structured case or narrative input. This is what separates
an "LLM wrapper" from a "clinical reasoning engine."

Strategy:
  1. Flatten all inputs into a single lowercase blob
  2. For each evidence string, check exact substring match
  3. Flag ungrounded claims in contradiction_or_quality_issues
  4. If hallucinations exceed threshold → inject a strong warning
"""
import json
import logging
from app.schemas.schemas import CaseAnalysisData

log = logging.getLogger(__name__)

HALLUCINATION_THRESHOLD = 3  # >3 ungrounded claims triggers a critical warning
MIN_EVIDENCE_LEN = 4         # ignore very short strings like "No" or "Yes"


def _flatten_input(structured_case: dict, narrative: str) -> str:
    """Build a single lowercase string of ALL input data."""
    return (json.dumps(structured_case, default=str) + " " + narrative).lower()


def _extract_evidence_strings(dx) -> list[tuple[str, str]]:
    """
    Pull all evidence strings from a differential's key_evidence.
    Returns list of (text, category) tuples.
    """
    results = []
    ev = dx.key_evidence
    if ev is None:
        return results

    if isinstance(ev, list):
        # Flat list: ["Positive ANA", "Low C3", ...]
        for item in ev:
            if isinstance(item, str):
                results.append((item, "support"))
            elif isinstance(item, dict):
                results.append((item.get("text", str(item)), "support"))

    elif isinstance(ev, dict):
        # {"support": [...], "against": [...]} or {"attributed_evidence": [...]}
        for key, val in ev.items():
            category = key  # "support", "against", "attributed_evidence", etc.
            if isinstance(val, list):
                for item in val:
                    if isinstance(item, str):
                        results.append((item, category))
                    elif isinstance(item, dict):
                        results.append((item.get("text", str(item)), category))
            elif isinstance(val, str):
                results.append((val, category))

    elif hasattr(ev, "support"):
        # EvidenceItem Pydantic model
        for s in ev.support:
            results.append((s, "support"))
        for s in ev.against:
            results.append((s, "against"))

    return results


def validate_grounding(
    analysis_data: CaseAnalysisData,
    structured_case: dict,
    narrative: str,
) -> list[str]:
    """
    Strict evidence grounding check.

    For every evidence string in top_differentials:
      - If it's a substring of the input blob → grounded ✅
      - If it starts with "Unknown" → exempt (valid uncertainty marker)
      - Otherwise → ungrounded ❌ → flagged

    Returns list of hallucination descriptions.
    Appends them to analysis_data.contradiction_or_quality_issues.
    """
    input_blob = _flatten_input(structured_case, narrative)
    hallucinations: list[str] = []

    for dx in analysis_data.top_differentials:
        evidence_pairs = _extract_evidence_strings(dx)

        for text, category in evidence_pairs:
            clean = text.strip()
            clean_lower = clean.lower()

            # Skip very short strings
            if len(clean) < MIN_EVIDENCE_LEN:
                continue

            # "Unknown: ..." is a valid uncertainty expression, not a hallucination
            if clean_lower.startswith("unknown"):
                continue

            # Strict substring check
            if clean_lower in input_blob:
                continue

            # Not found — this is an ungrounded claim
            label = f"{category.capitalize()} not grounded: \"{clean[:80]}\" (DX: {dx.name})"
            hallucinations.append(label)

    # Inject into quality issues
    for h in hallucinations:
        if h not in analysis_data.contradiction_or_quality_issues:
            analysis_data.contradiction_or_quality_issues.append(h)

    # Threshold warning
    if len(hallucinations) > HALLUCINATION_THRESHOLD:
        critical_msg = (
            f"⚠ GROUNDING ALERT: {len(hallucinations)} evidence claims could not be "
            f"traced to input data. Analysis reliability is degraded."
        )
        if critical_msg not in analysis_data.contradiction_or_quality_issues:
            analysis_data.contradiction_or_quality_issues.insert(0, critical_msg)
        log.warning(critical_msg)

    if hallucinations:
        log.info(
            "Grounding: %d/%d evidence items ungrounded for case",
            len(hallucinations),
            sum(len(_extract_evidence_strings(dx)) for dx in analysis_data.top_differentials),
        )
    else:
        log.info("Grounding: all evidence items verified ✅")

    return hallucinations
