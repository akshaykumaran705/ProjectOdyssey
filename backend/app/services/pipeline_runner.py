"""
Pipeline Runner — async-aware, failure-isolated pipeline orchestration.

Wraps the full ingest pipeline with:
  - Per-stage timing
  - Per-stage failure isolation (never 500 full pipeline)
  - Job status tracking
  - Resource preflight checks
"""
import datetime
import logging
import os
import time

from sqlalchemy.orm import Session

import app.models.models as model
import app.services.pdf_extractor as pdf_extractor
from app.services.canonical_narrative import build_canonical_narrative
from app.services.medasr_transcriber import transcribe_audio_bytes, compute_audio_hash
from app.services.image_captioner import caption_image_bytes, compute_image_hash
from app.services.source_hashing import compute_source_hash
import app.services.structured_case as structured_case_svc
from app.services.cost_engine import compute_cost_estimate
from app.services.rare_spotlight import compute_rare_spotlight
from app.services.trust_report_builder import build_trust_report
from app.services.builder import generate_case_analysis
from app.services.runner import LLMRunner
import app.utils.object_store as object_store

log = logging.getLogger(__name__)

# ── Resource Limits ──────────────────────────────────────────────
MAX_AUDIO_BYTES = 50 * 1024 * 1024    # 50MB
MAX_IMAGE_BYTES = 10 * 1024 * 1024    # 10MB
MAX_PDF_PAGES = 50
MAX_NARRATIVE_CHARS = 8000

DISCLAIMER = (
    "⚠ This system is for clinical decision support only. "
    "Not a replacement for physician judgment. All outputs "
    "should be verified by a qualified healthcare professional."
)


def _now():
    return datetime.datetime.utcnow()


def _s3_get(object_key: str) -> bytes:
    """Download object from S3."""
    s3 = object_store.object_store.client
    bucket = os.getenv("S3_BUCKET_NAME")
    resp = s3.get_object(Bucket=bucket, Key=object_key)
    return resp["Body"].read()


def create_ingest_job(db: Session, case_id: int) -> int:
    job = model.CaseJob(
        case_id=case_id,
        job_type="ingest_all",
        status="running",
        started_at=_now(),
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    return job.id

def run_full_ingest_background(job_id: int, case_id: int, user_id: int):
    from app.db.database import SessionLocal
    db = SessionLocal()
    try:
        run_full_ingest(db, case_id, user_id, job_id)
    finally:
        db.close()

def run_full_ingest(db: Session, case_id: int, user_id: int, job_id: int = None) -> dict:
    """
    Full ingest pipeline with failure isolation.

    Each stage is wrapped in try/except — failures are logged but never
    crash the entire pipeline. Returns full result with timing.
    """
    # Get or create job
    if job_id:
        job = db.query(model.CaseJob).filter(model.CaseJob.id == job_id).first()
    else:
        job = model.CaseJob(
            case_id=case_id,
            job_type="ingest_all",
            status="running",
            started_at=_now(),
        )
        db.add(job)
        db.commit()
        db.refresh(job)

    case = db.query(model.Cases).filter(
        model.Cases.id == case_id,
        model.Cases.created_by_user_id == user_id,
    ).first()

    timings = {}
    steps = []
    errors = []

    def _update_job_progress():
        if job:
            job.meta_data = {
                "steps": list(steps),
                "errors": list(errors),
                "timings": dict(timings)
            }
            db.commit()
            db.refresh(job)

    # ── 1. PDF Extraction ──
    t0 = time.time()
    try:
        pdf_extractor.process_pdf_extraction(db, case_id)
        steps.append("pdf_extraction")
    except Exception as e:
        errors.append(f"pdf_extraction: {e}")
        log.error("PDF extraction failed: %s", e)
    timings["pdf_extraction_ms"] = int((time.time() - t0) * 1000)
    _update_job_progress()

    # ── 2. Audio Transcription ──
    t0 = time.time()
    try:
        audio_files = db.query(model.CaseAudioFile).filter(
            model.CaseAudioFile.case_id == case_id
        ).all()
        tx_count = 0
        for af in audio_files:
            existing = db.query(model.CaseAudioTranscript).filter(
                model.CaseAudioTranscript.audio_file_id == af.id
            ).first()
            if existing:
                tx_count += 1
                continue
            try:
                audio_bytes = _s3_get(af.object_key)
                if len(audio_bytes) > MAX_AUDIO_BYTES:
                    errors.append(f"audio_{af.id}: exceeds {MAX_AUDIO_BYTES // (1024*1024)}MB limit")
                    continue
                result = transcribe_audio_bytes(audio_bytes)
                tx = model.CaseAudioTranscript(
                    case_id=case_id, audio_file_id=af.id,
                    transcript_text=result["text"],
                    extraction_method=result["method"],
                    model_name=result["model"],
                    source_hash=compute_audio_hash(audio_bytes),
                )
                db.add(tx)
                db.commit()
                tx_count += 1
            except Exception as e:
                errors.append(f"transcribe_audio_{af.id}: {e}")
                log.error("Audio transcription failed for file %d: %s", af.id, e)
        if tx_count > 0:
            steps.append(f"transcription({tx_count})")
    except Exception as e:
        errors.append(f"transcription: {e}")
        log.error("Transcription stage failed: %s", e)
    timings["transcription_ms"] = int((time.time() - t0) * 1000)
    _update_job_progress()

    # ── 3. Image Captioning ──
    t0 = time.time()
    try:
        image_files = db.query(model.CaseFiles).filter(
            model.CaseFiles.case_id == case_id,
            model.CaseFiles.content_type.in_(["image/png", "image/jpeg", "image/jpg"]),
        ).all()
        cap_count = 0
        for img in image_files:
            existing = db.query(model.CaseImageFinding).filter(
                model.CaseImageFinding.file_id == img.id
            ).first()
            if existing:
                cap_count += 1
                continue
            try:
                img_bytes = _s3_get(img.object_key)
                if len(img_bytes) > MAX_IMAGE_BYTES:
                    errors.append(f"image_{img.id}: exceeds {MAX_IMAGE_BYTES // (1024*1024)}MB limit")
                    continue
                result = caption_image_bytes(img_bytes, content_type=img.content_type)
                finding = model.CaseImageFinding(
                    case_id=case_id, file_id=img.id,
                    caption_text=result["text"],
                    extraction_method=result["method"],
                    model_name=result["model"],
                    source_hash=compute_image_hash(img_bytes),
                )
                db.add(finding)
                db.commit()
                cap_count += 1
            except Exception as e:
                errors.append(f"caption_image_{img.id}: {e}")
                log.error("Image captioning failed for file %d: %s", img.id, e)
        if cap_count > 0:
            steps.append(f"captioning({cap_count})")
    except Exception as e:
        errors.append(f"captioning: {e}")
        log.error("Captioning stage failed: %s", e)
    timings["captioning_ms"] = int((time.time() - t0) * 1000)
    _update_job_progress()

    # ── 4. Normalize ──
    t0 = time.time()
    try:
        case_fields = {
            "age": case.age, "sex": case.sex,
            "chief_complaint": case.chief_complaint,
            "history_present_illness": case.history_present_illness,
        }
        docs = db.query(model.CaseDocumentsText).filter(
            model.CaseDocumentsText.case_id == case_id
        ).all()
        extracted_docs = [{"file_id": d.file_id, "extracted_text": d.extracted_text} for d in docs]
        transcripts = db.query(model.CaseAudioTranscript).filter(
            model.CaseAudioTranscript.case_id == case_id
        ).all()
        image_findings = db.query(model.CaseImageFinding).filter(
            model.CaseImageFinding.case_id == case_id
        ).all()

        transcript_texts = [t.transcript_text for t in transcripts]
        caption_texts = [f.caption_text for f in image_findings]
        source_hash = compute_source_hash(
            case_fields, extracted_docs,
            transcripts=transcript_texts, image_captions=caption_texts,
        )

        narrative = build_canonical_narrative(case, docs, transcripts=transcripts, image_findings=image_findings)
        # Enforce narrative length limit
        if len(narrative) > MAX_NARRATIVE_CHARS:
            narrative = narrative[:MAX_NARRATIVE_CHARS] + "\n... [truncated]"
        case.narrative_text = narrative

        structured_result = structured_case_svc.narrative_to_structured_case(narrative)
        structured_json = structured_result.model_dump()
        existing = db.query(model.CaseStructured).filter(
            model.CaseStructured.case_id == case_id
        ).first()
        if existing:
            existing.source_hash = source_hash
            existing.normalized_data = structured_json
        else:
            db.add(model.CaseStructured(
                case_id=case_id, source_hash=source_hash, normalized_data=structured_json,
            ))
        db.commit()
        steps.append("normalize")
    except Exception as e:
        errors.append(f"normalize: {e}")
        log.error("Normalization failed: %s", e)
        # Mark job failed and return early
        job.status = "failed"
        job.error_message = str(e)
        job.finished_at = _now()
        job.meta_data = {"timings": timings, "steps": steps, "errors": errors}
        db.commit()
        return {"case_id": case_id, "job_id": job.id, "status": "failed", "errors": errors}
    timings["normalization_ms"] = int((time.time() - t0) * 1000)
    _update_job_progress()

    # ── 5. Analyze ──
    t0 = time.time()
    try:
        runner = LLMRunner(
            base_url="http://localhost:8080/",
            model="mlx-community/medgemma-4b-it-4bit",
        )
        struct_row = db.query(model.CaseStructured).filter(
            model.CaseStructured.case_id == case_id
        ).first()
        analysis_row, cache_hit = generate_case_analysis(
            db, case_id=case_id,
            structured_source_hash=struct_row.source_hash,
            structured_case=struct_row.normalized_data,
            narrative=narrative,
            analysis_version="v1", force=False, runner=runner,
        )
        steps.append("analyze")
    except Exception as e:
        errors.append(f"analyze: {e}")
        log.error("Analysis failed: %s", e)
        job.status = "failed"
        job.error_message = str(e)
        job.finished_at = _now()
        job.meta_data = {"timings": timings, "steps": steps, "errors": errors}
        db.commit()
        return {"case_id": case_id, "job_id": job.id, "status": "failed", "errors": errors}
    timings["analysis_ms"] = int((time.time() - t0) * 1000)
    _update_job_progress()

    result = {
        "case_id": case_id,
        "job_id": job.id,
        "source_hash": source_hash,
        "analysis_data": analysis_row.analysis_data,
        "cache_hit": cache_hit,
        "disclaimer": DISCLAIMER,
    }

    # ── 6. Cost Estimate (failure-isolated) ──
    t0 = time.time()
    try:
        est = compute_cost_estimate(analysis_row.analysis_data, struct_row.normalized_data)
        est_data = est.model_dump()
        # Persist
        existing_est = db.query(model.CaseCostEstimate).filter(
            model.CaseCostEstimate.case_id == case_id
        ).first()
        if existing_est:
            existing_est.estimate_data = est_data
            existing_est.source_hash = struct_row.source_hash
        else:
            db.add(model.CaseCostEstimate(
                case_id=case_id, estimate_data=est_data, source_hash=struct_row.source_hash,
            ))
        db.commit()
        result["cost_estimate"] = est_data
        steps.append("cost_estimate")
    except Exception as e:
        errors.append(f"cost_estimate: {e}")
        log.error("Cost estimate failed: %s", e)
    timings["cost_estimate_ms"] = int((time.time() - t0) * 1000)
    _update_job_progress()

    # ── 7. Rare Spotlight (failure-isolated) ──
    t0 = time.time()
    try:
        spot = compute_rare_spotlight(
            struct_row.normalized_data, analysis_row.analysis_data, narrative,
        )
        spot_data = spot.model_dump()
        existing_spot = db.query(model.CaseRareSpotlight).filter(
            model.CaseRareSpotlight.case_id == case_id
        ).first()
        if existing_spot:
            existing_spot.spotlight_data = spot_data
            existing_spot.source_hash = struct_row.source_hash
        else:
            db.add(model.CaseRareSpotlight(
                case_id=case_id, spotlight_data=spot_data, source_hash=struct_row.source_hash,
            ))
        db.commit()
        result["rare_spotlight"] = spot_data
        steps.append("rare_spotlight")
    except Exception as e:
        errors.append(f"rare_spotlight: {e}")
        log.error("Rare spotlight failed: %s", e)
    timings["spotlight_ms"] = int((time.time() - t0) * 1000)
    _update_job_progress()

    # ── 8. Trust Report (failure-isolated) ──
    t0 = time.time()
    try:
        trust = build_trust_report(struct_row.normalized_data, analysis_row.analysis_data, narrative)
        trust_data = trust.model_dump()
        existing_trust = db.query(model.CaseTrustReport).filter(
            model.CaseTrustReport.case_id == case_id
        ).first()
        if existing_trust:
            existing_trust.trust_data = trust_data
            existing_trust.source_hash = struct_row.source_hash
        else:
            db.add(model.CaseTrustReport(
                case_id=case_id, trust_data=trust_data, source_hash=struct_row.source_hash,
            ))
        db.commit()
        result["trust_report"] = trust_data
        steps.append("trust_report")
    except Exception as e:
        errors.append(f"trust_report: {e}")
        log.error("Trust report failed: %s", e)
    timings["trust_ms"] = int((time.time() - t0) * 1000)

    # ── Finalize job ──
    total_ms = sum(timings.values())
    job.status = "complete"
    job.finished_at = _now()
    job.meta_data = {
        "timings": timings,
        "total_ms": total_ms,
        "steps": steps,
        "errors": errors,
        "cache_hit": cache_hit,
    }
    db.commit()

    result["steps_completed"] = steps
    result["timings"] = timings
    result["total_ms"] = total_ms
    if errors:
        result["warnings"] = errors

    return result
