"""
Validator — enforces clinical analysis quality rules.

Instead of raising exceptions (the 4B model can't reliably meet all
constraints), it **appends quality issues** to the analysis data so
the frontend can display warnings.
"""
import logging
from app.schemas.schemas import CaseAnalysisData

log = logging.getLogger(__name__)


def enforce_analysis_rules(data: CaseAnalysisData) -> list[str]:
    """
    Best-effort quality checks.  Appends issues to
    data.contradiction_or_quality_issues and returns the list of warnings.
    """
    warnings: list[str] = []

    # --- differentials ---
    for dx in data.top_differentials:
        ev = dx.key_evidence
        if ev is None:
            warnings.append(f"DX '{dx.name}': key_evidence is missing")
        elif isinstance(ev, dict):
            support = ev.get("support", [])
            against = ev.get("against", ev.get("against_or_unknown", []))
            if isinstance(support, list) and len(support) < 2:
                warnings.append(f"DX '{dx.name}': <2 supporting evidence items")
            if isinstance(against, list) and len(against) < 1:
                warnings.append(f"DX '{dx.name}': no against/unknown evidence")
        elif isinstance(ev, list):
            if len(ev) < 2:
                warnings.append(f"DX '{dx.name}': <2 supporting evidence items")
        elif hasattr(ev, "support"):
            if len(ev.support) < 2:
                warnings.append(f"DX '{dx.name}': <2 supporting evidence items")
            if len(ev.against) < 1:
                warnings.append(f"DX '{dx.name}': no against/unknown evidence")

    # --- missing info breadth ---
    any_low_med = any(
        dx.confidence in ("low", "medium")
        for dx in data.top_differentials
        if dx.confidence
    )
    if any_low_med and len(data.missing_info) < 5:
        warnings.append(
            "missing_info has <5 items but differentials include low/medium confidence"
        )

    # --- triage gate ---
    if data.care_setting_recommendation == "ED_now":
        steps = data.recommended_next_steps
        if isinstance(steps, list):
            has_stat = any(
                (isinstance(s, dict) and s.get("priority") == "stat")
                or (hasattr(s, "priority") and getattr(s, "priority", None) == "stat")
                for s in steps
            )
            if not has_stat:
                warnings.append(
                    "care_setting is ED_now but no next step has priority 'stat'"
                )

    # Append all warnings to the analysis data itself
    if warnings:
        for w in warnings:
            log.warning("Analysis quality: %s", w)
            if w not in data.contradiction_or_quality_issues:
                data.contradiction_or_quality_issues.append(w)

    return warnings