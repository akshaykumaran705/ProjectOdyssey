"""
Uncertainty Scoring — deterministic, transparent confidence scoring.

Don't let confidence be purely LLM-generated. Use rule-based scoring:

Base: 50
  + evidence support points
  + lab count bonus
  + timeline bonus
  - missing tests penalty
  - low support ratio penalty
  - safety flags penalty

Output: confidence_score (0–100) + confidence_level + uncertainty_reasons.
"""
import logging
from app.schemas.schema_trust import DiagnosisTrust, SafetyFlag

log = logging.getLogger(__name__)


def score_diagnosis(
    dx_trust: DiagnosisTrust,
    structured_case: dict,
    analysis_data: dict,
    safety_flags: list[SafetyFlag],
) -> DiagnosisTrust:
    """
    Compute deterministic confidence score for a single diagnosis.
    Mutates and returns dx_trust with scored fields.
    """
    score = 50
    reasons: list[str] = []

    # ── Positive signals ──

    # +5 per supported evidence item (cap +30)
    supported = sum(1 for e in dx_trust.evidence_links if e.supported)
    ev_bonus = min(supported * 5, 30)
    score += ev_bonus

    # +10 if ≥3 abnormal labs
    labs = structured_case.get("abnormal_labs", [])
    if len(labs) >= 3:
        score += 10

    # +10 if clear timeline exists
    timeline = structured_case.get("timeline", {})
    if isinstance(timeline, dict):
        has_onset = bool(timeline.get("onset"))
        has_duration = bool(timeline.get("duration"))
        if has_onset and has_duration:
            score += 10

    # ── Negative signals ──

    # -10 if significant missing info
    missing = analysis_data.get("missing_info", [])
    if isinstance(missing, list) and len(missing) >= 2:
        score -= 10
        for m in missing[:3]:
            reasons.append(f"Missing: {m}")

    # -15 if safety red flags but no confirmatory data
    critical_flags = [f for f in safety_flags if f.severity in ("critical", "high")]
    if critical_flags and len(labs) < 2:
        score -= 15
        reasons.append("Critical safety flags without sufficient confirmatory labs")

    # -20 if support ratio < 0.5
    if dx_trust.support_ratio < 0.5:
        score -= 20
        unsupported = [e.claim for e in dx_trust.evidence_links if not e.supported]
        reasons.append(f"Low evidence grounding ({dx_trust.support_ratio:.0%}) — {len(unsupported)} unsupported claims")

    # -5 per unsupported evidence claim
    unsupported_count = sum(1 for e in dx_trust.evidence_links if not e.supported)
    score -= unsupported_count * 5

    # Clamp 0–100
    score = max(0, min(100, score))

    # Map to level
    if score >= 80:
        level = "high"
    elif score >= 50:
        level = "medium"
    else:
        level = "low"

    if not reasons and level == "low":
        reasons.append("Insufficient evidence to support high confidence")

    dx_trust.confidence_score = score
    dx_trust.confidence_level = level
    dx_trust.uncertainty_reasons = reasons

    return dx_trust


def score_all(
    diagnoses: list[DiagnosisTrust],
    structured_case: dict,
    analysis_data: dict,
    safety_flags: list[SafetyFlag],
) -> list[DiagnosisTrust]:
    """Score all diagnoses and return updated list."""
    for dx in diagnoses:
        score_diagnosis(dx, structured_case, analysis_data, safety_flags)

    if diagnoses:
        avg = sum(d.confidence_score for d in diagnoses) / len(diagnoses)
        log.info(
            "Uncertainty scoring: %d diagnoses, avg score %d",
            len(diagnoses), int(avg),
        )

    return diagnoses
