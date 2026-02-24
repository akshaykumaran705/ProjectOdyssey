"""
Evidence Linker — post-processing that annotates evidence strings
with their source location in the structured case.

Enables UI highlighting and "why did you say that?" explainability.
"""
import logging
from app.schemas.schemas import CaseAnalysisData

log = logging.getLogger(__name__)


def _find_source(text: str, structured_case: dict) -> str | None:
    """
    Try to locate which structured_case field contains this evidence text.
    Returns a source path like "structured.abnormal_labs[2]" or None.
    """
    text_lower = text.lower().strip()

    # Check symptom lists
    for i, sym in enumerate(structured_case.get("symptoms", [])):
        if text_lower in sym.lower() or sym.lower() in text_lower:
            return f"structured.symptoms[{i}]"

    # Check exam findings
    for i, ef in enumerate(structured_case.get("exam_findings", [])):
        if text_lower in ef.lower() or ef.lower() in text_lower:
            return f"structured.exam_findings[{i}]"

    # Check abnormal labs
    for i, lab in enumerate(structured_case.get("abnormal_labs", [])):
        lab_str = str(lab).lower()
        if text_lower in lab_str or (lab.get("name", "").lower() in text_lower and lab.get("name")):
            return f"structured.abnormal_labs[{i}]"

    # Check medications
    for i, med in enumerate(structured_case.get("medications", [])):
        if text_lower in med.lower() or med.lower() in text_lower:
            return f"structured.medications[{i}]"

    # Check comorbidities
    for i, cm in enumerate(structured_case.get("comorbidities", [])):
        if text_lower in cm.lower() or cm.lower() in text_lower:
            return f"structured.comorbidities[{i}]"

    # Check red flags
    for i, rf in enumerate(structured_case.get("red_flags", [])):
        if text_lower in rf.lower() or rf.lower() in text_lower:
            return f"structured.red_flags[{i}]"

    # Check family history
    for i, fh in enumerate(structured_case.get("family_history", [])):
        if text_lower in fh.lower() or fh.lower() in text_lower:
            return f"structured.family_history[{i}]"

    # Check top-level fields
    for field in ("chief_complaint", "history_present_illness"):
        val = structured_case.get(field, "")
        if val and text_lower in val.lower():
            return f"structured.{field}"

    return None


def link_evidence(analysis_data: CaseAnalysisData, structured_case: dict) -> int:
    """
    For each differential's evidence, find the source field in the structured
    case and annotate it.  Converts flat lists into attributed dicts.

    Returns number of evidence items successfully linked.
    """
    linked_count = 0

    for dx in analysis_data.top_differentials:
        ev = dx.key_evidence
        if ev is None:
            continue

        # Normalize to a list of strings
        if isinstance(ev, list):
            evidence_strings = [str(e) for e in ev]
        elif isinstance(ev, dict):
            evidence_strings = []
            for v in ev.values():
                if isinstance(v, list):
                    evidence_strings.extend(str(e) for e in v)
                elif isinstance(v, str):
                    evidence_strings.append(v)
        else:
            continue

        # Build attributed evidence
        attributed = []
        for text in evidence_strings:
            source = _find_source(text, structured_case)
            entry = {"text": text, "source": source}
            attributed.append(entry)
            if source:
                linked_count += 1

        # Replace key_evidence with attributed version
        dx.key_evidence = {"attributed_evidence": attributed}

    log.info("Evidence linker: %d items linked to sources", linked_count)
    return linked_count
