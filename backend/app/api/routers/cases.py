import io
import uuid
from fastapi import APIRouter, Depends, HTTPException, File, UploadFile, Query
import app.schemas.schemas as schema
import app.models.models as model
import app.services.pdf_extractor as pdf_extractor
import app.services.narrative_builder as narrative_builder
import app.utils.object_store as object_store
import app.services.case_analysis as case_analysis
from app.services.builder import generate_case_analysis
from app.services.runner import LLMRunner
from app.services.source_hashing import compute_source_hash
import app.services.structured_case as structured_case
from app.services.cost_engine import compute_cost_estimate
from app.services.rare_spotlight import compute_rare_spotlight
from app.services.trust_report_builder import build_trust_report
from app.services.canonical_narrative import build_canonical_narrative
from app.services.medasr_transcriber import transcribe_audio_bytes, compute_audio_hash
from app.services.image_captioner import caption_image_bytes, compute_image_hash
from app.api.deps import db_dependency, get_current_user_from_token
from typing import Optional, List

router = APIRouter(prefix="/cases", tags=["cases"])

@router.post("")
async def create_case(case: schema.CaseCreate, db: db_dependency, current_user: model.Users = Depends(get_current_user_from_token)):
    if not case.title or not case.chief_complaint:
        return {"error": "Title and chief complaint are required"}
    first_user = db.query(model.Users).first()
    if not first_user:
        return {"error": "No users found. Please register first."}
    new_case = model.Cases(
        created_by_user_id=current_user.id,
        title=case.title,
        chief_complaint=case.chief_complaint,
        history_present_illness=case.history_present_illness,
        age=case.age,
        sex=case.sex
    )
    db.add(new_case)
    db.commit()
    db.refresh(new_case)
    return {"message": "Case created successfully", "case_id": new_case.id}

@router.get("")
async def get_cases(current_user: model.Users = Depends(get_current_user_from_token), db: db_dependency = None):
    cases = db.query(model.Cases).filter(model.Cases.created_by_user_id == current_user.id).all()
    return {"cases": [{"id": c.id, "title": c.title, "chief_complaint": c.chief_complaint, "created_by_user_id": c.created_by_user_id} for c in cases]}

@router.get("/{case_id}")
async def get_case(case_id: int, db: db_dependency = None, current_user: model.Users = Depends(get_current_user_from_token)):
    case = db.query(model.Cases).filter(model.Cases.id == case_id, model.Cases.created_by_user_id == current_user.id).first()
    if not case:
        return {"error": "Case not found"}
    return {"case": {"id": case.id, "title": case.title, "chief_complaint": case.chief_complaint, "created_by_user_id": case.created_by_user_id}}

@router.post("/{case_id}/files")
async def upload_case_file(case_id: int, file: UploadFile = File(...), db: db_dependency = None, current_user: model.Users = Depends(get_current_user_from_token)):
    if file.content_type not in ["application/pdf", "image/png", "image/jpeg"]:
        return {"error": "Unsupported file type"}
    data = await file.read()
    size = len(data)
    if size > 5 * 1024 * 1024:
        return {"error": "File size exceeds limit"}
    key = f"case_{case_id}/{uuid.uuid4()}-{file.filename}"
    case = db.query(model.Cases).filter(model.Cases.id == case_id, model.Cases.created_by_user_id == current_user.id).first()
    if not case:
        return {"Error": "Case not found"}
    new_file = model.CaseFiles(case_id=case_id, file_name=file.filename, content_type=file.content_type, object_key=key, size_bytes=size)
    db.add(new_file)
    db.commit()
    db.refresh(new_file)
    object_store.object_store.upload_fileobj(fileobj=io.BytesIO(data), key=key, content_type=file.content_type)
    return {"File Uploaded Successfully": key, "size": size}

@router.post("/{case_id}/normalize")
async def normalize_case_data(case_id: int, db: db_dependency = None, current_user: model.Users = Depends(get_current_user_from_token)):
    case = db.query(model.Cases).filter(model.Cases.id == case_id, model.Cases.created_by_user_id == current_user.id).first()
    if not case:
        return {"error": "Case not found"}
    pdf_extractor.process_pdf_extraction(db, case_id)
    case_fields = {
        "age": case.age,
        "sex": case.sex,
        "chief_complaint": case.chief_complaint,
        "history_present_illness": case.history_present_illness
    }
    docs = db.query(model.CaseDocumentsText).filter(model.CaseDocumentsText.case_id == case.id).all()
    extracted_docs = [{
        "file_id": d.file_id,
        "extracted_text": d.extracted_text,
    } for d in docs]

    # Phase 7: include transcripts + image captions in source hash
    transcripts = db.query(model.CaseAudioTranscript).filter(model.CaseAudioTranscript.case_id == case_id).all()
    image_findings = db.query(model.CaseImageFinding).filter(model.CaseImageFinding.case_id == case_id).all()
    transcript_texts = [t.transcript_text for t in transcripts if t.transcript_text]
    caption_texts = [f.caption_text for f in image_findings if f.caption_text]

    source_hash = compute_source_hash(case_fields, extracted_docs, transcripts=transcript_texts, image_captions=caption_texts)
    existing = db.query(model.CaseStructured).filter(model.CaseStructured.case_id == case_id).first()
    if existing and existing.source_hash == source_hash:
        return {
            "case_id": case_id,
            "status": "already_normalized",
            "source_hash": source_hash
        }

    # Phase 7: canonical narrative merges all modalities
    narrative = build_canonical_narrative(case, docs, transcripts=transcripts, image_findings=image_findings)
    case.narrative_text = narrative
    structured = structured_case.narrative_to_structured_case(narrative)
    structured_json = structured.model_dump()
    if existing:
        existing.source_hash = source_hash
        existing.normalized_data = structured_json
        db.commit()
        db.refresh(existing)
    else:
        new_case = model.CaseStructured(case_id=case.id, source_hash=source_hash, normalized_data=structured_json)
        db.add(new_case)
        db.commit()
        db.refresh(new_case)
    return {
        "message": "Case Normalized",
        "case_id": case_id,
        "status": "Normalized",
        "structured_case": structured_json,
        "source_hash": source_hash,
        "documents_extracted": len(docs),
        "transcripts_included": len(transcript_texts),
        "image_captions_included": len(caption_texts),
        "narrative": narrative[:1500]
    }

@router.post("/{case_id}/analyze")
def analyze_case(
    case_id: int,
    body: schema.AnalyzeRequest,
    include: Optional[str] = Query(None, description="Comma-separated: spotlight,estimate"),
    db: db_dependency = None,
    current_user=Depends(get_current_user_from_token),
):
    case = db.query(model.Cases).filter(model.Cases.id == case_id, model.Cases.created_by_user_id == current_user.id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    
    structured = db.query(model.CaseStructured).filter(model.CaseStructured.case_id == case_id).first()
    if not structured:
        raise HTTPException(status_code=400, detail="Case not normalized yet")
    narrative_text = case.narrative_text if hasattr(case, "narrative_text") else ""
    if not narrative_text:
        narrative_text = ""
    runner = LLMRunner(base_url="http://localhost:8080/", model="mlx-community/medgemma-4b-it-4bit")
    analysis_row, cache_hit = generate_case_analysis(db, case_id=case_id, structured_source_hash=structured.source_hash, structured_case=structured.normalized_data, narrative=narrative_text, analysis_version=body.analysis_version, force=body.force, runner=runner)

    result = {
        "case_id": analysis_row.case_id,
        "source_hash": analysis_row.source_hash,
        "analysis_version": analysis_row.analysis_version,
        "analysis_data": analysis_row.analysis_data,
        "cache_hit": cache_hit,
        "created_at": analysis_row.created_at,
    }

    # Phase 5A: include flags
    includes = [s.strip().lower() for s in (include or "").split(",")] if include else []

    if "estimate" in includes:
        result["cost_estimate"] = _run_estimate(db, case_id, structured, analysis_row)

    if "spotlight" in includes:
        result["rare_spotlight"] = _run_spotlight(db, case_id, structured, analysis_row, narrative_text)

    if "trust" in includes:
        result["trust_report"] = _run_trust(db, case_id, structured, analysis_row, narrative_text)

    return result

@router.get("/{case_id}/analysis")
def get_analysis(
    case_id: int,
    analysis_version: str = "v1",
    source_hash: str = None,
    db: db_dependency = None,
    current_user=Depends(get_current_user_from_token),
):
    case = db.query(model.Cases).filter(
        model.Cases.id == case_id,
        model.Cases.created_by_user_id == current_user.id,
    ).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    row = case_analysis.get_latest_case_analysis(
        db, case_id=case_id, analysis_version=analysis_version, source_hash=source_hash
    )
    if not row:
        raise HTTPException(status_code=404, detail="No analysis found for this case")

    struct = db.query(model.CaseStructured).filter(model.CaseStructured.case_id == case_id).first()

    return {
        "case_id": row.case_id,
        "source_hash": row.source_hash,
        "analysis_version": row.analysis_version,
        "analysis_data": row.analysis_data,
        "structured_case": struct.normalized_data if struct else None,
        "narrative": case.narrative_text if hasattr(case, "narrative_text") else "",
        "cache_hit": True,
        "created_at": row.created_at,
    }


# ── Phase 5: UI endpoints ──────────────────────────────────────────

@router.get("/{case_id}/summary")
def get_case_summary(
    case_id: int,
    analysis_version: str = "v1",
    db: db_dependency = None,
    current_user=Depends(get_current_user_from_token),
):
    """UI-optimized clinical summary card."""
    case = db.query(model.Cases).filter(
        model.Cases.id == case_id,
        model.Cases.created_by_user_id == current_user.id,
    ).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    row = case_analysis.get_latest_case_analysis(
        db, case_id=case_id, analysis_version=analysis_version
    )
    if not row:
        raise HTTPException(status_code=404, detail="No analysis found")

    ad = row.analysis_data or {}
    differentials = ad.get("top_differentials", [])

    # Top 3 differentials (name + confidence)
    top_3 = [
        {"name": dx.get("name", "Unknown"), "confidence": dx.get("confidence", "?")}
        for dx in differentials[:3]
    ]

    # Immediate actions (priority = stat)
    all_steps = ad.get("recommended_next_steps", [])
    immediate = []
    if isinstance(all_steps, list):
        for s in all_steps:
            if isinstance(s, dict) and s.get("priority") in ("stat", "today"):
                immediate.append(s.get("action", ""))

    # Key red flags across all differentials
    red_flags = set()
    for dx in differentials:
        for rf in dx.get("red_flags", []):
            red_flags.add(rf)

    return {
        "case_id": case_id,
        "top_3_differentials": top_3,
        "immediate_actions": immediate[:5],
        "key_red_flags": list(red_flags)[:5],
        "one_paragraph_summary": ad.get("summary", "No summary available."),
        "care_setting": ad.get("care_setting_recommendation", "unknown"),
        "quality_issues": ad.get("contradiction_or_quality_issues", []),
    }


@router.get("/{case_id}/analysis/compare")
def compare_analyses(
    case_id: int,
    hash1: str,
    hash2: str,
    analysis_version: str = "v1",
    db: db_dependency = None,
    current_user=Depends(get_current_user_from_token),
):
    """Compare two analysis versions for the same case."""
    case = db.query(model.Cases).filter(
        model.Cases.id == case_id,
        model.Cases.created_by_user_id == current_user.id,
    ).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    row1 = case_analysis.get_latest_case_analysis(
        db, case_id=case_id, analysis_version=analysis_version, source_hash=hash1
    )
    row2 = case_analysis.get_latest_case_analysis(
        db, case_id=case_id, analysis_version=analysis_version, source_hash=hash2
    )

    if not row1 or not row2:
        raise HTTPException(status_code=404, detail="One or both analyses not found")

    ad1 = row1.analysis_data or {}
    ad2 = row2.analysis_data or {}

    # Compare differentials
    dx1_names = [dx.get("name", "") for dx in ad1.get("top_differentials", [])]
    dx2_names = [dx.get("name", "") for dx in ad2.get("top_differentials", [])]

    added_dx = [n for n in dx2_names if n not in dx1_names]
    removed_dx = [n for n in dx1_names if n not in dx2_names]

    # Compare confidence changes
    confidence_changes = []
    dx1_map = {dx.get("name"): dx.get("confidence") for dx in ad1.get("top_differentials", [])}
    dx2_map = {dx.get("name"): dx.get("confidence") for dx in ad2.get("top_differentials", [])}
    for name in set(dx1_map) & set(dx2_map):
        if dx1_map[name] != dx2_map[name]:
            confidence_changes.append({
                "diagnosis": name,
                "from": dx1_map[name],
                "to": dx2_map[name],
            })

    # Compare triage
    triage1 = ad1.get("care_setting_recommendation", "?")
    triage2 = ad2.get("care_setting_recommendation", "?")

    return {
        "case_id": case_id,
        "hash1": hash1,
        "hash2": hash2,
        "triage_change": {
            "from": triage1,
            "to": triage2,
            "changed": triage1 != triage2,
        },
        "differentials": {
            "added": added_dx,
            "removed": removed_dx,
            "confidence_changes": confidence_changes,
        },
        "summary_v1": (ad1.get("summary") or "")[:200],
        "summary_v2": (ad2.get("summary") or "")[:200],
    }


# ── Phase 5A: Helper functions ──────────────────────────────────

def _run_estimate(db, case_id, structured, analysis_row) -> dict:
    """Compute or return cached cost estimate."""
    existing = db.query(model.CaseCostEstimate).filter(
        model.CaseCostEstimate.case_id == case_id
    ).first()
    if existing and existing.source_hash == structured.source_hash:
        return existing.estimate_data

    estimate = compute_cost_estimate(
        analysis_data=analysis_row.analysis_data,
        structured_case=structured.normalized_data,
    )
    data = estimate.model_dump()

    if existing:
        existing.estimate_data = data
        existing.source_hash = structured.source_hash
        db.commit()
    else:
        obj = model.CaseCostEstimate(
            case_id=case_id,
            estimate_data=data,
            source_hash=structured.source_hash,
        )
        db.add(obj)
        db.commit()
    return data


def _run_spotlight(db, case_id, structured, analysis_row, narrative) -> dict:
    """Compute or return cached rare disease spotlight."""
    existing = db.query(model.CaseRareSpotlight).filter(
        model.CaseRareSpotlight.case_id == case_id
    ).first()
    if existing and existing.source_hash == structured.source_hash:
        return existing.spotlight_data

    spotlight = compute_rare_spotlight(
        structured_case=structured.normalized_data,
        analysis_data=analysis_row.analysis_data,
        narrative=narrative,
    )
    data = spotlight.model_dump()

    if existing:
        existing.spotlight_data = data
        existing.source_hash = structured.source_hash
        db.commit()
    else:
        obj = model.CaseRareSpotlight(
            case_id=case_id,
            spotlight_data=data,
            source_hash=structured.source_hash,
        )
        db.add(obj)
        db.commit()
    return data


# ── Phase 5A: Dedicated endpoints ───────────────────────────────

@router.post("/{case_id}/estimate")
def compute_estimate(
    case_id: int,
    db: db_dependency = None,
    current_user=Depends(get_current_user_from_token),
):
    case = db.query(model.Cases).filter(
        model.Cases.id == case_id,
        model.Cases.created_by_user_id == current_user.id,
    ).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    structured = db.query(model.CaseStructured).filter(
        model.CaseStructured.case_id == case_id
    ).first()
    if not structured:
        raise HTTPException(status_code=400, detail="Case not normalized yet")

    analysis = case_analysis.get_latest_case_analysis(db, case_id=case_id, analysis_version="v1")
    if not analysis:
        raise HTTPException(status_code=400, detail="Analyze case first")

    data = _run_estimate(db, case_id, structured, analysis)
    return {"case_id": case_id, "estimate": data, "source_hash": structured.source_hash}


@router.get("/{case_id}/estimate")
def get_estimate(
    case_id: int,
    db: db_dependency = None,
    current_user=Depends(get_current_user_from_token),
):
    case = db.query(model.Cases).filter(
        model.Cases.id == case_id,
        model.Cases.created_by_user_id == current_user.id,
    ).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    row = db.query(model.CaseCostEstimate).filter(
        model.CaseCostEstimate.case_id == case_id
    ).first()
    if not row:
        raise HTTPException(status_code=404, detail="No cost estimate found — run POST /estimate first")

    return {"case_id": case_id, "estimate": row.estimate_data, "source_hash": row.source_hash}


@router.post("/{case_id}/spotlight")
def compute_spotlight(
    case_id: int,
    db: db_dependency = None,
    current_user=Depends(get_current_user_from_token),
):
    case = db.query(model.Cases).filter(
        model.Cases.id == case_id,
        model.Cases.created_by_user_id == current_user.id,
    ).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    structured = db.query(model.CaseStructured).filter(
        model.CaseStructured.case_id == case_id
    ).first()
    if not structured:
        raise HTTPException(status_code=400, detail="Case not normalized yet")

    analysis = case_analysis.get_latest_case_analysis(db, case_id=case_id, analysis_version="v1")
    if not analysis:
        raise HTTPException(status_code=400, detail="Analyze case first")

    narrative_text = ""
    data = _run_spotlight(db, case_id, structured, analysis, narrative_text)
    return {"case_id": case_id, "spotlight": data, "source_hash": structured.source_hash}


@router.get("/{case_id}/spotlight")
def get_spotlight(
    case_id: int,
    db: db_dependency = None,
    current_user=Depends(get_current_user_from_token),
):
    case = db.query(model.Cases).filter(
        model.Cases.id == case_id,
        model.Cases.created_by_user_id == current_user.id,
    ).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    row = db.query(model.CaseRareSpotlight).filter(
        model.CaseRareSpotlight.case_id == case_id
    ).first()
    if not row:
        raise HTTPException(status_code=404, detail="No spotlight found — run POST /spotlight first")

    return {"case_id": case_id, "spotlight": row.spotlight_data, "source_hash": row.source_hash}


# ── Phase 6: Trust Report helpers + endpoints ─────────────────

def _run_trust(db, case_id, structured, analysis_row, narrative) -> dict:
    """Compute or return cached trust report."""
    existing = db.query(model.CaseTrustReport).filter(
        model.CaseTrustReport.case_id == case_id
    ).first()
    if existing and existing.source_hash == structured.source_hash:
        return existing.trust_data

    report = build_trust_report(
        structured_case=structured.normalized_data,
        analysis_data=analysis_row.analysis_data,
        narrative=narrative,
    )
    data = report.model_dump()

    if existing:
        existing.trust_data = data
        existing.source_hash = structured.source_hash
        db.commit()
    else:
        obj = model.CaseTrustReport(
            case_id=case_id,
            trust_data=data,
            source_hash=structured.source_hash,
        )
        db.add(obj)
        db.commit()
    return data


@router.post("/{case_id}/trust_report")
def compute_trust_report(
    case_id: int,
    db: db_dependency = None,
    current_user=Depends(get_current_user_from_token),
):
    case = db.query(model.Cases).filter(
        model.Cases.id == case_id,
        model.Cases.created_by_user_id == current_user.id,
    ).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    structured = db.query(model.CaseStructured).filter(
        model.CaseStructured.case_id == case_id
    ).first()
    if not structured:
        raise HTTPException(status_code=400, detail="Case not normalized yet")

    analysis = case_analysis.get_latest_case_analysis(db, case_id=case_id, analysis_version="v1")
    if not analysis:
        raise HTTPException(status_code=400, detail="Analyze case first")

    narrative_text = ""
    data = _run_trust(db, case_id, structured, analysis, narrative_text)
    return {"case_id": case_id, "trust_report": data, "source_hash": structured.source_hash}


@router.get("/{case_id}/trust_report")
def get_trust_report(
    case_id: int,
    db: db_dependency = None,
    current_user=Depends(get_current_user_from_token),
):
    case = db.query(model.Cases).filter(
        model.Cases.id == case_id,
        model.Cases.created_by_user_id == current_user.id,
    ).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    row = db.query(model.CaseTrustReport).filter(
        model.CaseTrustReport.case_id == case_id
    ).first()
    if not row:
        raise HTTPException(status_code=404, detail="No trust report found — run POST /trust_report first")

    return {"case_id": case_id, "trust_report": row.trust_data, "source_hash": row.source_hash}


# ── Phase 7: Multimodal Ingestion endpoints ─────────────────────

AUDIO_TYPES = {"audio/mpeg", "audio/wav", "audio/x-m4a", "audio/mp4", "audio/x-wav", "audio/ogg", "audio/webm"}


@router.post("/{case_id}/audio")
async def upload_audio(
    case_id: int,
    file: UploadFile = File(...),
    db: db_dependency = None,
    current_user=Depends(get_current_user_from_token),
):
    case = db.query(model.Cases).filter(
        model.Cases.id == case_id, model.Cases.created_by_user_id == current_user.id
    ).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    if file.content_type not in AUDIO_TYPES:
        raise HTTPException(status_code=400, detail=f"Unsupported audio type: {file.content_type}. Accepted: {AUDIO_TYPES}")

    data = await file.read()
    size = len(data)
    if size > 50 * 1024 * 1024:  # 50MB limit
        raise HTTPException(status_code=400, detail="Audio file too large (max 50MB)")

    key = f"case_{case_id}/audio/{uuid.uuid4()}-{file.filename}"
    object_store.object_store.upload_fileobj(fileobj=io.BytesIO(data), key=key, content_type=file.content_type)

    audio_file = model.CaseAudioFile(
        case_id=case_id,
        file_name=file.filename,
        object_key=key,
        content_type=file.content_type,
        size_bytes=size,
    )
    db.add(audio_file)
    db.commit()
    db.refresh(audio_file)

    return {"audio_file_id": audio_file.id, "object_key": key, "size_bytes": size}


@router.post("/{case_id}/transcribe")
def transcribe_case_audio(
    case_id: int,
    db: db_dependency = None,
    current_user=Depends(get_current_user_from_token),
):
    case = db.query(model.Cases).filter(
        model.Cases.id == case_id, model.Cases.created_by_user_id == current_user.id
    ).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    audio_files = db.query(model.CaseAudioFile).filter(
        model.CaseAudioFile.case_id == case_id
    ).all()
    if not audio_files:
        raise HTTPException(status_code=400, detail="No audio files uploaded yet")

    results = []
    for af in audio_files:
        # Check if transcript already exists with same hash
        existing = db.query(model.CaseAudioTranscript).filter(
            model.CaseAudioTranscript.audio_file_id == af.id
        ).first()

        # Download audio bytes from S3
        try:
            import os
            s3 = object_store.object_store.client
            bucket = os.getenv("S3_BUCKET_NAME")
            resp = s3.get_object(Bucket=bucket, Key=af.object_key)
            audio_bytes = resp["Body"].read()
        except Exception as e:
            results.append({"audio_file_id": af.id, "error": f"Failed to download: {e}"})
            continue

        audio_hash = compute_audio_hash(audio_bytes)
        if existing and existing.source_hash == audio_hash:
            results.append({
                "audio_file_id": af.id,
                "status": "already_transcribed",
                "preview": existing.transcript_text[:200],
            })
            continue

        # Transcribe
        result = transcribe_audio_bytes(audio_bytes)

        if existing:
            existing.transcript_text = result["text"]
            existing.source_hash = audio_hash
            existing.extraction_method = result["method"]
            existing.model_name = result["model"]
            db.commit()
        else:
            tx = model.CaseAudioTranscript(
                case_id=case_id,
                audio_file_id=af.id,
                transcript_text=result["text"],
                extraction_method=result["method"],
                model_name=result["model"],
                source_hash=audio_hash,
            )
            db.add(tx)
            db.commit()

        results.append({
            "audio_file_id": af.id,
            "status": "transcribed",
            "method": result["method"],
            "preview": result["text"][:200],
        })

    return {"case_id": case_id, "transcripts_processed": len(results), "results": results}


@router.post("/{case_id}/caption_images")
def caption_case_images(
    case_id: int,
    db: db_dependency = None,
    current_user=Depends(get_current_user_from_token),
):
    case = db.query(model.Cases).filter(
        model.Cases.id == case_id, model.Cases.created_by_user_id == current_user.id
    ).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    image_files = db.query(model.CaseFiles).filter(
        model.CaseFiles.case_id == case_id,
        model.CaseFiles.content_type.in_(["image/png", "image/jpeg", "image/jpg"]),
    ).all()
    if not image_files:
        raise HTTPException(status_code=400, detail="No image files uploaded yet")

    results = []
    for img_file in image_files:
        existing = db.query(model.CaseImageFinding).filter(
            model.CaseImageFinding.file_id == img_file.id
        ).first()

        # Download image bytes
        try:
            import os
            s3 = object_store.object_store.client
            bucket = os.getenv("S3_BUCKET_NAME")
            resp = s3.get_object(Bucket=bucket, Key=img_file.object_key)
            img_bytes = resp["Body"].read()
        except Exception as e:
            results.append({"file_id": img_file.id, "error": f"Failed to download: {e}"})
            continue

        img_hash = compute_image_hash(img_bytes)
        if existing and existing.source_hash == img_hash:
            results.append({
                "file_id": img_file.id,
                "status": "already_captioned",
                "preview": existing.caption_text[:200],
            })
            continue

        # Caption
        result = caption_image_bytes(img_bytes, content_type=img_file.content_type)

        if existing:
            existing.caption_text = result["text"]
            existing.source_hash = img_hash
            existing.extraction_method = result["method"]
            existing.model_name = result["model"]
            db.commit()
        else:
            finding = model.CaseImageFinding(
                case_id=case_id,
                file_id=img_file.id,
                caption_text=result["text"],
                extraction_method=result["method"],
                model_name=result["model"],
                source_hash=img_hash,
            )
            db.add(finding)
            db.commit()

        results.append({
            "file_id": img_file.id,
            "status": "captioned",
            "method": result["method"],
            "preview": result["text"][:200],
        })

    return {"case_id": case_id, "images_processed": len(results), "results": results}


from fastapi import BackgroundTasks

@router.post("/{case_id}/ingest_all")
def ingest_all(
    case_id: int,
    background_tasks: BackgroundTasks,
    db: db_dependency = None,
    current_user=Depends(get_current_user_from_token),
):
    """
    One-click pipeline: PDF → transcribe → caption → normalize →
    analyze → cost → spotlight → trust.
    Failure-isolated, timed, job-tracked.
    """
    from app.services.pipeline_runner import create_ingest_job, run_full_ingest_background
    job_id = create_ingest_job(db, case_id)
    background_tasks.add_task(run_full_ingest_background, job_id, case_id, current_user.id)
    return {"message": "Pipeline started in background", "job_id": job_id}


@router.get("/jobs/{job_id}")
def get_job_status(
    job_id: int,
    db: db_dependency = None,
    current_user=Depends(get_current_user_from_token),
):
    """Get status of a pipeline job."""
    job = db.query(model.CaseJob).filter(model.CaseJob.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    # Verify ownership
    case = db.query(model.Cases).filter(
        model.Cases.id == job.case_id,
        model.Cases.created_by_user_id == current_user.id,
    ).first()
    if not case:
        raise HTTPException(status_code=404, detail="Job not found")
    return {
        "job_id": job.id,
        "case_id": job.case_id,
        "job_type": job.job_type,
        "status": job.status,
        "started_at": job.started_at,
        "finished_at": job.finished_at,
        "error_message": job.error_message,
        "meta_data": job.meta_data,
    }
