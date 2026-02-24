"""
Safety Rules Engine — deterministic clinical safety flags.

Scans structured_case for critical findings and generates
severity-graded safety flags with recommendations.
"""
import logging
import re
from typing import Any

from app.schemas.schema_trust import SafetyFlag

log = logging.getLogger(__name__)


def _get_lab_value(structured_case: dict, lab_name: str) -> float | None:
    """Extract a numeric lab value by name (case-insensitive)."""
    for lab in structured_case.get("abnormal_labs", []):
        if not isinstance(lab, dict):
            continue
        name = (lab.get("name") or "").lower()
        if lab_name.lower() in name:
            val = lab.get("value", "")
            # Extract first number from value string
            m = re.search(r"(\d+\.?\d*)", str(val))
            if m:
                return float(m.group(1))
    return None


def _has_symptom(structured_case: dict, *keywords: str) -> tuple[bool, str]:
    """Check if any keyword appears in symptoms, exam_findings, or chief_complaint."""
    search_fields = {
        "symptoms": structured_case.get("symptoms", []),
        "exam_findings": structured_case.get("exam_findings", []),
        "red_flags": structured_case.get("red_flags", []),
    }

    cc = structured_case.get("chief_complaint") or ""
    hpi = structured_case.get("history_present_illness") or ""
    text_blob = (cc + " " + hpi).lower()

    for field_name, items in search_fields.items():
        if isinstance(items, list):
            for i, item in enumerate(items):
                item_lower = str(item).lower()
                for kw in keywords:
                    if kw.lower() in item_lower:
                        return True, f"structured_case.{field_name}[{i}]"

    for kw in keywords:
        if kw.lower() in text_blob:
            return True, "structured_case.chief_complaint/hpi"

    return False, ""


def evaluate_safety_rules(structured_case: dict) -> list[SafetyFlag]:
    """
    Run all deterministic safety rules against the case data.
    Returns severity-graded safety flags.
    """
    flags: list[SafetyFlag] = []

    # ── Vital Sign Rules ──

    # Hypoxia
    spo2 = _get_lab_value(structured_case, "spo2")
    if spo2 is None:
        spo2 = _get_lab_value(structured_case, "oxygen")
    if spo2 is not None and spo2 <= 92:
        severity = "critical" if spo2 <= 88 else "high"
        flags.append(SafetyFlag(
            flag="Hypoxia detected",
            severity=severity,
            triggered_by=[f"SpO2 = {spo2}%"],
            recommendation="Immediate supplemental O2. Consider emergent workup for PE, pneumonia, or cardiac cause.",
        ))

    # ── Lab Rules ──

    # Hyperkalemia
    k = _get_lab_value(structured_case, "potassium")
    if k is not None and k >= 5.5:
        severity = "critical" if k >= 6.5 else "high" if k >= 6.0 else "medium"
        flags.append(SafetyFlag(
            flag="Hyperkalemia",
            severity=severity,
            triggered_by=[f"Potassium = {k} mEq/L"],
            recommendation="Stat ECG. Calcium gluconate if peaked T-waves. Consider insulin/glucose, kayexalate.",
        ))

    # Hyponatremia
    na = _get_lab_value(structured_case, "sodium")
    if na is not None and na <= 125:
        severity = "critical" if na <= 120 else "high"
        flags.append(SafetyFlag(
            flag="Severe hyponatremia",
            severity=severity,
            triggered_by=[f"Sodium = {na} mEq/L"],
            recommendation="Fluid restriction. Slow correction to avoid osmotic demyelination. Nephrology consult.",
        ))

    # Elevated troponin
    trop = _get_lab_value(structured_case, "troponin")
    if trop is not None and trop > 0.04:
        severity = "critical" if trop > 1.0 else "high" if trop > 0.1 else "medium"
        flags.append(SafetyFlag(
            flag="Elevated troponin — possible myocardial injury",
            severity=severity,
            triggered_by=[f"Troponin = {trop}"],
            recommendation="Serial troponins. Stat ECG. Cardiology consult if STEMI pattern.",
        ))

    # Elevated creatinine
    cr = _get_lab_value(structured_case, "creatinine")
    if cr is not None and cr > 2.0:
        severity = "high" if cr > 4.0 else "medium"
        flags.append(SafetyFlag(
            flag="Elevated creatinine — acute kidney concern",
            severity=severity,
            triggered_by=[f"Creatinine = {cr}"],
            recommendation="Evaluate for AKI vs CKD. Check urine output, hydration status. Nephrology if rapid rise.",
        ))

    # Elevated WBC
    wbc = _get_lab_value(structured_case, "wbc")
    if wbc is None:
        wbc = _get_lab_value(structured_case, "white blood")
    if wbc is not None and wbc > 20:
        severity = "high" if wbc > 30 else "medium"
        flags.append(SafetyFlag(
            flag="Marked leukocytosis",
            severity=severity,
            triggered_by=[f"WBC = {wbc}"],
            recommendation="Blood cultures. Evaluate for infection, leukemia, or stress response.",
        ))

    # Low platelets
    plt = _get_lab_value(structured_case, "platelet")
    if plt is not None and plt < 50:
        severity = "critical" if plt < 20 else "high"
        flags.append(SafetyFlag(
            flag="Severe thrombocytopenia",
            severity=severity,
            triggered_by=[f"Platelets = {plt}"],
            recommendation="Bleeding precautions. Hematology consult. Evaluate for TTP/HIT/DIC.",
        ))

    # ── Compound Rules ──

    # Chest pain + SOB + elevated troponin → ACS
    has_cp, cp_path = _has_symptom(structured_case, "chest pain", "substernal", "crushing")
    has_sob, sob_path = _has_symptom(structured_case, "shortness of breath", "dyspnea", "sob")
    if has_cp and trop is not None and trop > 0.04:
        flags.append(SafetyFlag(
            flag="ACS risk — chest pain with troponin elevation",
            severity="critical",
            triggered_by=[cp_path, f"Troponin={trop}"],
            recommendation="Activate cath lab protocol if STEMI. Aspirin, heparin, serial ECGs.",
        ))

    # Proteinuria + low complement + cytopenias → lupus nephritis
    has_prot, prot_path = _has_symptom(structured_case, "proteinuria", "protein in urine")
    c3 = _get_lab_value(structured_case, "c3")
    c4 = _get_lab_value(structured_case, "c4")
    low_comp = (c3 is not None and c3 < 80) or (c4 is not None and c4 < 15)
    if has_prot and low_comp:
        flags.append(SafetyFlag(
            flag="Possible lupus nephritis",
            severity="high",
            triggered_by=[prot_path, f"C3={c3}", f"C4={c4}"],
            recommendation="Urgent nephrology referral. Anti-dsDNA, renal biopsy consideration.",
        ))

    # Altered mental status
    has_ams, ams_path = _has_symptom(structured_case, "altered mental", "confusion", "obtunded", "unresponsive")
    if has_ams:
        flags.append(SafetyFlag(
            flag="Altered mental status",
            severity="critical",
            triggered_by=[ams_path],
            recommendation="Stat glucose, head CT, toxicology screen. Rule out stroke, sepsis, metabolic.",
        ))

    # Fever + immunosuppression
    has_fever, fever_path = _has_symptom(structured_case, "fever", "febrile")
    has_immuno, immuno_path = _has_symptom(structured_case, "immunosuppress", "transplant", "chemotherapy", "hiv")
    if has_fever and has_immuno:
        flags.append(SafetyFlag(
            flag="Febrile in immunocompromised patient",
            severity="critical",
            triggered_by=[fever_path, immuno_path],
            recommendation="Immediate blood cultures, broad-spectrum antibiotics. Infectious disease consult.",
        ))

    log.info("Safety rules: %d flags triggered", len(flags))
    return flags
