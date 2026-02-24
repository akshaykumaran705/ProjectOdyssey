"""
Health + Metrics — system observability endpoints.
"""
from fastapi import APIRouter, Depends
from sqlalchemy import func
from app.api.deps import db_dependency
import app.models.models as model

router = APIRouter(tags=["health"])


@router.get("/health")
async def health_check():
    return {"status": "ok"}


@router.get("/metrics")
def get_metrics(db: db_dependency = None):
    """
    System metrics: latency averages, cache hit rate, job stats.
    """
    # Job stats
    total_jobs = db.query(func.count(model.CaseJob.id)).scalar() or 0
    complete_jobs = db.query(func.count(model.CaseJob.id)).filter(
        model.CaseJob.status == "complete"
    ).scalar() or 0
    failed_jobs = db.query(func.count(model.CaseJob.id)).filter(
        model.CaseJob.status == "failed"
    ).scalar() or 0

    # Analysis cache hit rate
    total_logs = db.query(func.count(model.AnalysisLog.id)).scalar() or 0
    cache_hits = db.query(func.count(model.AnalysisLog.id)).filter(
        model.AnalysisLog.cache_hit == 1
    ).scalar() or 0

    # Average latency from analysis logs
    avg_latency = db.query(func.avg(model.AnalysisLog.latency_ms)).filter(
        model.AnalysisLog.cache_hit == 0
    ).scalar()

    # Average timings from completed jobs
    avg_timings = {}
    completed = db.query(model.CaseJob).filter(
        model.CaseJob.status == "complete",
        model.CaseJob.meta_data.isnot(None),
    ).order_by(model.CaseJob.id.desc()).limit(20).all()

    if completed:
        timing_keys = ["pdf_extraction_ms", "transcription_ms", "captioning_ms",
                       "normalization_ms", "analysis_ms", "cost_estimate_ms",
                       "spotlight_ms", "trust_ms"]
        for key in timing_keys:
            vals = []
            for j in completed:
                t = (j.meta_data or {}).get("timings", {}).get(key)
                if t is not None:
                    vals.append(t)
            if vals:
                avg_timings[f"avg_{key}"] = int(sum(vals) / len(vals))

    # Counts
    total_cases = db.query(func.count(model.Cases.id)).scalar() or 0
    total_analyses = db.query(func.count(model.CaseAnalysis.id)).scalar() or 0
    total_trust = db.query(func.count(model.CaseTrustReport.id)).scalar() or 0
    total_estimates = db.query(func.count(model.CaseCostEstimate.id)).scalar() or 0
    total_spotlights = db.query(func.count(model.CaseRareSpotlight.id)).scalar() or 0

    return {
        "status": "operational",
        "counts": {
            "total_cases": total_cases,
            "total_analyses": total_analyses,
            "trust_reports": total_trust,
            "cost_estimates": total_estimates,
            "rare_spotlights": total_spotlights,
        },
        "jobs": {
            "total": total_jobs,
            "complete": complete_jobs,
            "failed": failed_jobs,
        },
        "cache": {
            "total_analysis_runs": total_logs,
            "cache_hits": cache_hits,
            "cache_hit_rate": round(cache_hits / max(total_logs, 1), 3),
        },
        "latency": {
            "avg_analysis_ms": int(avg_latency) if avg_latency else 0,
            **avg_timings,
        },
    }
