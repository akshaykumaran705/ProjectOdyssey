"""
Confidence Calibration Layer — deterministic post-processing heuristics.

Boosts or overrides model-generated confidence based on structured case
evidence patterns. Makes the system more deterministic and less
hallucination-prone.
"""
import logging
from app.schemas.schemas import CaseAnalysisData

log = logging.getLogger(__name__)

# ── Rule definitions ────────────────────────────────────────────────
# Each rule: (dx_name_keywords, required_evidence_keywords, action)
BOOST_RULES = [
    {
        "name": "SLE boost",
        "dx_keywords": ["lupus", "sle"],
        "evidence_keywords": ["ana", "anti-dsdna", "complement", "c3", "c4", "malar", "rash"],
        "min_matches": 3,
        "target_confidence": "high",
    },
    {
        "name": "MI boost",
        "dx_keywords": ["myocardial infarction", "mi", "stemi", "nstemi", "acute coronary"],
        "evidence_keywords": ["st elevation", "troponin", "chest pain", "diaphoresis"],
        "min_matches": 2,
        "target_confidence": "high",
    },
    {
        "name": "PE boost",
        "dx_keywords": ["pulmonary embolism", "pe"],
        "evidence_keywords": ["d-dimer", "tachycardia", "dyspnea", "pleuritic", "dvt", "wells"],
        "min_matches": 3,
        "target_confidence": "high",
    },
    {
        "name": "Pneumonia boost",
        "dx_keywords": ["pneumonia", "cap"],
        "evidence_keywords": ["consolidation", "wbc", "procalcitonin", "fever", "crackles", "sputum"],
        "min_matches": 3,
        "target_confidence": "high",
    },
    {
        "name": "Heart failure boost",
        "dx_keywords": ["heart failure", "chf", "adhf", "decompensated"],
        "evidence_keywords": ["bnp", "edema", "jvp", "jugular", "s3", "crackles", "orthopnea", "dyspnea"],
        "min_matches": 3,
        "target_confidence": "high",
    },
    {
        "name": "DKA boost",
        "dx_keywords": ["diabetic ketoacidosis", "dka"],
        "evidence_keywords": ["glucose", "ketone", "acidosis", "ph", "bicarbonate", "anion gap"],
        "min_matches": 3,
        "target_confidence": "high",
    },
]


def _get_evidence_text(dx) -> str:
    """Flatten all evidence for a differential into a single lower-case string."""
    parts = []
    ev = dx.key_evidence
    if isinstance(ev, list):
        parts.extend(str(e) for e in ev)
    elif isinstance(ev, dict):
        for v in ev.values():
            if isinstance(v, list):
                parts.extend(str(e) for e in v)
            elif isinstance(v, str):
                parts.append(v)
    elif hasattr(ev, "support"):
        parts.extend(ev.support)
        parts.extend(ev.against)
    if dx.rationale:
        parts.append(dx.rationale)
    return " ".join(parts).lower()


def calibrate_confidence(analysis_data: CaseAnalysisData, structured_case: dict) -> int:
    """
    Apply deterministic heuristic rules to boost confidence where
    structured evidence strongly supports a diagnosis.

    Returns the number of calibrations applied.
    """
    # Build a merged evidence blob from the structured case
    sc_blob = str(structured_case).lower()
    calibrations = 0

    for dx in analysis_data.top_differentials:
        dx_name_lower = (dx.name or "").lower()
        evidence_blob = _get_evidence_text(dx) + " " + sc_blob

        for rule in BOOST_RULES:
            # Check if this rule's dx keywords match the differential name
            if not any(kw in dx_name_lower for kw in rule["dx_keywords"]):
                continue

            # Count how many evidence keywords are present
            matches = sum(
                1 for kw in rule["evidence_keywords"] if kw in evidence_blob
            )

            if matches >= rule["min_matches"]:
                old_conf = dx.confidence
                if old_conf != rule["target_confidence"]:
                    dx.confidence = rule["target_confidence"]
                    log.info(
                        "Calibrated '%s' confidence: %s → %s (rule: %s, %d/%d matches)",
                        dx.name,
                        old_conf,
                        rule["target_confidence"],
                        rule["name"],
                        matches,
                        rule["min_matches"],
                    )
                    calibrations += 1

    return calibrations
