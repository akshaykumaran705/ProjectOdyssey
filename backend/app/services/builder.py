"""
Orchestrator — the main analysis pipeline.

Flow:
  1. Check cache → return if hit
  2. Run LLM → extract analysis data
  3. Calibrate confidence (deterministic heuristics)
  4. Link evidence to structured case sources
  5. Safety escalation guardrail
  6. Hallucination detection (production module)
  7. Validate quality rules
  8. Persist analysis + observability log
"""
import logging

from sqlalchemy.orm import Session

from app.services.case_analysis import get_case_analysis, create_case_analysis
from app.utils.cache import compute_analysis_source_hash, compute_narrative_hash
from app.services.runner import LLMRunner
from app.utils.prompts import PROMPT_VERSION
from app.services.validator import enforce_analysis_rules
from app.services.calibrator import calibrate_confidence
from app.services.evidence_linker import link_evidence
from app.services.safety import apply_safety_escalation
from app.schemas.schemas import AnalysisMeta, InputHashes
from app.models.models import AnalysisLog

# Production hallucination module
from hallucination.detector import detect_hallucinations
from hallucination.config import HallucinationConfig

log = logging.getLogger(__name__)


def generate_case_analysis(
    db: Session,
    *,
    case_id: int,
    structured_source_hash: str,
    structured_case: dict,
    narrative: str,
    analysis_version: str,
    force: bool,
    runner: LLMRunner,
):
    narrative_hash = compute_narrative_hash(narrative)
    source_hash = compute_analysis_source_hash(
        structured_source_hash=structured_source_hash,
        narrative=narrative,
        analysis_version=analysis_version,
    )

    # ── 1. cache check ──
    if not force:
        existing = get_case_analysis(db, case_id, source_hash, analysis_version)
        if existing:
            _persist_log(db, case_id=case_id, analysis_id=existing.id,
                         model_id=runner.model, cache_hit=True, latency_ms=0)
            return existing, True

    # ── 2. run LLM ──
    analysis_data, latency_ms = runner.analyze(
        structured_case=structured_case,
        narrative=narrative,
        max_differentials=3,
        include_probabilities=False,
    )

    # ── 3. calibrate confidence ──
    calibrations = calibrate_confidence(analysis_data, structured_case)

    # ── 4. link evidence to sources ──
    linked = link_evidence(analysis_data, structured_case)

    # ── 5. safety escalation ──
    escalated = apply_safety_escalation(analysis_data, structured_case, narrative)

    # ── 6. hallucination detection (production module) ──
    hallucination_report = detect_hallucinations(
        structured_case=structured_case,
        narrative=narrative,
        analysis_data=analysis_data.model_dump(),
        documents=None,
        cfg=HallucinationConfig(mode="warn"),
    )

    # Promote findings into quality issues for UI
    for f in hallucination_report.findings:
        if f.severity in ("warning", "error"):
            msg = f"[hallucination:{f.severity}] {f.category}: {f.claim[:120]}"
            if msg not in analysis_data.contradiction_or_quality_issues:
                analysis_data.contradiction_or_quality_issues.append(msg)

    # ── 7. validate quality ──
    warnings = enforce_analysis_rules(analysis_data)

    # stamp meta
    if not analysis_data.meta:
        analysis_data.meta = AnalysisMeta(prompt_version="")
    if not analysis_data.input_hashes:
        analysis_data.input_hashes = InputHashes(
            structred_source_hash="", narrative_hash=""
        )

    analysis_data.meta.model_id = runner.model
    analysis_data.meta.latency_ms = str(latency_ms)
    analysis_data.meta.prompt_version = PROMPT_VERSION
    analysis_data.meta.grounding_failures = hallucination_report.stats.get("errors", 0)
    analysis_data.meta.calibrations_applied = calibrations
    analysis_data.meta.evidence_linked = linked
    analysis_data.meta.safety_escalated = escalated
    analysis_data.input_hashes.structred_source_hash = structured_source_hash
    analysis_data.input_hashes.narrative_hash = narrative_hash

    # Attach full hallucination report to analysis_data for storage
    dump = analysis_data.model_dump()
    dump.setdefault("meta", {})
    dump["meta"]["hallucination"] = hallucination_report.model_dump()

    # ── 8. persist ──
    created = create_case_analysis(
        db,
        case_id=case_id,
        source_hash=source_hash,
        analysis_version=analysis_version,
        analysis_data=dump,
        model_id=runner.model,
        latency_ms=latency_ms,
    )

    # observability log
    _persist_log(
        db,
        case_id=case_id,
        analysis_id=created.id,
        model_id=runner.model,
        cache_hit=False,
        latency_ms=latency_ms,
        calibrations=calibrations,
        evidence_linked=linked,
        hallucinations=hallucination_report.stats.get("findings_total", 0),
        safety_escalated=escalated,
        validation_warnings=warnings,
    )

    return created, False


def _persist_log(
    db: Session,
    *,
    case_id: int,
    analysis_id: int | None = None,
    model_id: str = "",
    cache_hit: bool = False,
    latency_ms: int = 0,
    calibrations: int = 0,
    evidence_linked: int = 0,
    hallucinations: int = 0,
    safety_escalated: bool = False,
    validation_warnings: list[str] | None = None,
):
    """Write an AnalysisLog row for observability."""
    try:
        entry = AnalysisLog(
            case_id=case_id,
            analysis_id=analysis_id,
            model_id=model_id,
            prompt_version=PROMPT_VERSION,
            latency_ms=latency_ms,
            cache_hit=1 if cache_hit else 0,
            calibrations_applied=calibrations,
            evidence_linked=evidence_linked,
            hallucinations_found=hallucinations,
            safety_escalated=1 if safety_escalated else 0,
            validation_warnings=validation_warnings or [],
        )
        db.add(entry)
        db.commit()
    except Exception as e:
        log.warning("Failed to persist analysis log: %s", e)
        db.rollback()
