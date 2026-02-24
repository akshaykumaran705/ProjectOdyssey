"""
Case analysis data access layer.
"""
from sqlalchemy.orm import Session
from app.models.models import CaseAnalysis
from typing import Optional


def get_case_analysis(
    db: Session, case_id: int, source_hash: str, analysis_version: str
) -> Optional[CaseAnalysis]:
    """Exact match by case_id + source_hash + version."""
    return (
        db.query(CaseAnalysis)
        .filter(
            CaseAnalysis.case_id == case_id,
            CaseAnalysis.source_hash == source_hash,
            CaseAnalysis.analysis_version == analysis_version,
        )
        .first()
    )


def get_latest_case_analysis(
    db: Session,
    case_id: int,
    analysis_version: str,
    source_hash: Optional[str] = None,
) -> Optional[CaseAnalysis]:
    """Latest analysis for a case, optionally filtered by source_hash."""
    q = db.query(CaseAnalysis).filter(
        CaseAnalysis.case_id == case_id,
        CaseAnalysis.analysis_version == analysis_version,
    )
    if source_hash:
        q = q.filter(CaseAnalysis.source_hash == source_hash)
    return q.order_by(CaseAnalysis.created_at.desc()).first()


def create_case_analysis(
    db: Session,
    *,
    case_id: int,
    source_hash: str,
    analysis_version: str,
    analysis_data: dict,
    model_id: str | None = None,
    latency_ms: int | None = None,
) -> CaseAnalysis:
    # Upsert: if the same case_id/source_hash/version exists, update it
    existing = db.query(CaseAnalysis).filter(
        CaseAnalysis.case_id == case_id,
        CaseAnalysis.source_hash == source_hash,
        CaseAnalysis.analysis_version == analysis_version,
    ).first()
    if existing:
        existing.analysis_data = analysis_data
        db.commit()
        db.refresh(existing)
        return existing

    obj = CaseAnalysis(
        case_id=case_id,
        source_hash=source_hash,
        analysis_version=analysis_version,
        analysis_data=analysis_data,
    )
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj
