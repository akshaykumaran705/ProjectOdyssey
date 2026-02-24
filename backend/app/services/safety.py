"""
Safety Escalation Guardrail — deterministic override that prevents
unsafe LLM downgrades of care setting.

Before returning analysis, scans for red-flag keywords in evidence
and narrative. If found, overrides care_setting_recommendation to ED_now.
"""
import logging
from app.schemas.schemas import CaseAnalysisData

log = logging.getLogger(__name__)

RED_FLAG_KEYWORDS = [
    "hypotension",
    "systolic < 90",
    "sbp < 90",
    "severe dyspnea",
    "respiratory distress",
    "active bleeding",
    "hemorrhage",
    "altered mental status",
    "unresponsive",
    "confusion",
    "syncope",
    "st elevation",
    "stemi",
    "cardiac arrest",
    "anaphylaxis",
    "sepsis",
    "septic shock",
    "status epilepticus",
    "stroke",
    "acute abdomen",
    "tension pneumothorax",
    "intubation",
    "cyanosis",
    "spo2 < 90",
    "oxygen saturation 88",
    "oxygen saturation 89",
    "oxygen saturation 85",
    "gcs < 8",
]


def apply_safety_escalation(
    analysis_data: CaseAnalysisData,
    structured_case: dict,
    narrative: str,
) -> bool:
    """
    Scan the analysis data, structured case, and narrative for red flags.
    If any are found, override care_setting_recommendation to ED_now.

    Returns True if escalation was applied.
    """
    if analysis_data.care_setting_recommendation == "ED_now":
        return False  # already at highest level

    # Build a combined text blob to scan
    blob_parts = [narrative, str(structured_case)]

    # Also include evidence from differentials
    for dx in analysis_data.top_differentials:
        ev = dx.key_evidence
        if isinstance(ev, list):
            blob_parts.extend(str(e) for e in ev)
        elif isinstance(ev, dict):
            for v in ev.values():
                if isinstance(v, list):
                    blob_parts.extend(str(e) for e in v)
                elif isinstance(v, str):
                    blob_parts.append(v)
        blob_parts.extend(dx.red_flags)

    blob = " ".join(blob_parts).lower()

    triggered = [kw for kw in RED_FLAG_KEYWORDS if kw in blob]

    if triggered:
        old_setting = analysis_data.care_setting_recommendation
        analysis_data.care_setting_recommendation = "ED_now"
        msg = f"Safety escalation: {old_setting} → ED_now (triggered by: {', '.join(triggered[:3])})"
        log.warning(msg)
        analysis_data.contradiction_or_quality_issues.append(msg)

        # Ensure there's a stat triage step
        if isinstance(analysis_data.recommended_next_steps, list):
            has_stat = any(
                (isinstance(s, dict) and s.get("priority") == "stat")
                for s in analysis_data.recommended_next_steps
            )
            if not has_stat:
                analysis_data.recommended_next_steps.insert(0, {
                    "category": "triage",
                    "priority": "stat",
                    "action": "Immediate clinical evaluation required",
                    "rationale": f"Red flags detected: {', '.join(triggered[:3])}",
                })

        return True

    return False
