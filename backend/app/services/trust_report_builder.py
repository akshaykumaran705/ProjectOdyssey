"""
Trust Report Builder — orchestrates all Phase 6 components.

Flow:
  1. Build evidence index from structured case + narrative
  2. Verify analysis evidence claims
  3. Run safety rules
  4. Compute deterministic confidence scores
  5. Determine overall trust status
  6. Return TrustReport
"""
import logging

from app.schemas.schema_trust import TrustReport
from app.services.evidence_verifier import verify_analysis
from app.services.safety_rules import evaluate_safety_rules
from app.services.uncertainty_scoring import score_all

log = logging.getLogger(__name__)


def build_trust_report(
    structured_case: dict,
    analysis_data: dict,
    narrative: str = "",
) -> TrustReport:
    """
    Build a complete trust report for a case analysis.
    Purely deterministic — no LLM calls.
    """
    # 1. Verify evidence claims
    diagnoses = verify_analysis(analysis_data, structured_case, narrative)

    # 2. Run safety rules
    safety_flags = evaluate_safety_rules(structured_case)

    # 3. Score confidence
    scored_diagnoses = score_all(diagnoses, structured_case, analysis_data, safety_flags)

    # 4. Compute overall metrics
    if scored_diagnoses:
        overall_support = sum(d.support_ratio for d in scored_diagnoses) / len(scored_diagnoses)
        overall_confidence = sum(d.confidence_score for d in scored_diagnoses) // len(scored_diagnoses)
    else:
        overall_support = 0.0
        overall_confidence = 0

    total_claims = sum(len(d.evidence_links) for d in scored_diagnoses)
    supported_claims = sum(
        sum(1 for e in d.evidence_links if e.supported) for d in scored_diagnoses
    )
    unsupported_claims = total_claims - supported_claims
    critical_flags = [f for f in safety_flags if f.severity in ("critical",)]
    high_flags = [f for f in safety_flags if f.severity in ("high",)]

    # 5. Determine overall status
    global_warnings: list[str] = []

    if overall_support < 0.4:
        status = "fail"
        global_warnings.append(
            f"Evidence grounding critically low ({overall_support:.0%}). "
            f"{unsupported_claims}/{total_claims} claims unsupported."
        )
    elif overall_support < 0.7 or critical_flags:
        status = "warn"
        if overall_support < 0.7:
            global_warnings.append(
                f"Evidence grounding below threshold ({overall_support:.0%}). "
                f"{unsupported_claims} unsupported claims detected."
            )
        for f in critical_flags:
            global_warnings.append(f"Critical safety flag: {f.flag}")
    else:
        status = "ok"

    if high_flags and status == "ok":
        status = "warn"
        for f in high_flags:
            global_warnings.append(f"Safety concern: {f.flag}")

    # Add unsupported claim details
    for dx in scored_diagnoses:
        for ev in dx.evidence_links:
            if not ev.supported:
                global_warnings.append(
                    f"Unsupported claim in {dx.diagnosis}: \"{ev.claim[:80]}\""
                )

    report = TrustReport(
        status=status,
        overall_support_ratio=round(overall_support, 3),
        overall_confidence=overall_confidence,
        safety_flags=safety_flags,
        diagnoses=scored_diagnoses,
        global_warnings=global_warnings,
        stats={
            "total_claims": total_claims,
            "supported_claims": supported_claims,
            "unsupported_claims": unsupported_claims,
            "safety_flags_total": len(safety_flags),
            "critical_flags": len(critical_flags),
        },
    )

    log.info(
        "Trust report: status=%s, support=%.0f%%, confidence=%d, flags=%d",
        status, overall_support * 100, overall_confidence, len(safety_flags),
    )

    return report
