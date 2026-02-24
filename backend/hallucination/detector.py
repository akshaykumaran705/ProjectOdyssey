"""
Hallucination Detector — the main engine.

Scans all claims in CaseAnalysisData against the evidence index
using token Jaccard + numeric anchoring. Produces a HallucinationReport
with severity-graded findings.

Adapted to ProjectOdyssey's exact schema where:
  - DxItem.key_evidence is Any (list, dict, EvidenceItem, or attributed_evidence)
  - recommended_next_steps is Any (list of dicts or NextStep models)
  - summary is Optional[str]
"""
import logging
from typing import Any, Dict, List, Optional, Tuple

from .config import HallucinationConfig
from .index import build_evidence_index, EvidenceItem
from .normalize import norm_text
from .rules import token_jaccard, token_containment, numeric_compatible, is_generic_advice
from .report import HallucinationReport, Finding, EvidenceHit

log = logging.getLogger(__name__)


# ── Matching ──────────────────────────────────────────────────────

def _best_hits(
    claim_norm: str,
    evidence: List[EvidenceItem],
    cfg: HallucinationConfig,
) -> List[EvidenceHit]:
    """Find the best matching evidence items for a claim."""
    hits: List[EvidenceHit] = []

    for it in evidence:
        if not it.norm:
            continue

        # Use the max of Jaccard and containment (containment is better
        # when evidence text is much longer than the claim)
        j_score = token_jaccard(claim_norm, it.norm)
        c_score = token_containment(claim_norm, it.norm)
        score = max(j_score, c_score)

        if score >= cfg.min_ngram_hit_score:
            # Also check numeric compatibility — fabricated numbers are caught here
            if numeric_compatible(claim_norm, it.norm):
                hits.append(EvidenceHit(
                    source=it.source,
                    path=it.path,
                    snippet=it.raw[:200],
                    score=round(float(score), 3),
                ))

    hits.sort(key=lambda h: h.score, reverse=True)
    return hits[:cfg.max_hits_per_claim]


# ── Claim Extraction ─────────────────────────────────────────────

def _extract_evidence_strings(ev: Any) -> List[Tuple[str, str]]:
    """
    Extract (text, sub_category) pairs from DxItem.key_evidence.
    Handles all known shapes: list, dict, EvidenceItem, attributed_evidence.
    """
    results: List[Tuple[str, str]] = []

    if ev is None:
        return results

    if isinstance(ev, list):
        for item in ev:
            if isinstance(item, str):
                results.append((item, "support"))
            elif isinstance(item, dict):
                results.append((item.get("text", str(item)), "support"))

    elif isinstance(ev, dict):
        # Handle multiple dict shapes
        for key, val in ev.items():
            sub_cat = key  # "support", "against", "attributed_evidence", etc.
            if isinstance(val, list):
                for item in val:
                    if isinstance(item, str):
                        results.append((item, sub_cat))
                    elif isinstance(item, dict):
                        results.append((item.get("text", str(item)), sub_cat))
            elif isinstance(val, str):
                results.append((val, sub_cat))

    elif hasattr(ev, "support"):
        # EvidenceItem Pydantic model
        for s in getattr(ev, "support", []):
            results.append((s, "support"))
        for s in getattr(ev, "against", []):
            results.append((s, "against"))

    return results


def _iter_claims_from_analysis(
    analysis_data: Dict[str, Any],
    cfg: HallucinationConfig,
) -> List[Tuple[str, str]]:
    """
    Extract all (category, claim_text) pairs to verify.
    Adapted to ProjectOdyssey's CaseAnalysisData schema.
    """
    claims: List[Tuple[str, str]] = []

    # ── Evidence (hard check) ──
    for dx in analysis_data.get("top_differentials", [])[:10]:
        ev = dx.get("key_evidence")
        for text, sub_cat in _extract_evidence_strings(ev):
            claims.append(("evidence", text))

        # Red flags are patient-specific facts — verify strictly
        for rf in (dx.get("red_flags") or []):
            if isinstance(rf, str):
                claims.append(("red_flags", rf))

        # Rationale (soft check)
        if cfg.check_rationale and dx.get("rationale"):
            claims.append(("rationale", str(dx["rationale"])))

    # ── Summary (soft check) ──
    if cfg.check_summary and analysis_data.get("summary"):
        claims.append(("summary", str(analysis_data["summary"])))

    # ── Next steps (soft check) ──
    if cfg.check_next_steps:
        steps = analysis_data.get("recommended_next_steps", [])
        if isinstance(steps, list):
            for step in steps[:20]:
                if isinstance(step, dict):
                    if step.get("action"):
                        claims.append(("next_steps", str(step["action"])))
                    if step.get("rationale"):
                        claims.append(("next_steps", str(step["rationale"])))
                elif hasattr(step, "action"):
                    claims.append(("next_steps", str(step.action)))

    # Cap total claims
    out: List[Tuple[str, str]] = []
    for cat, c in claims:
        c = (c or "").strip()
        if not c:
            continue
        out.append((cat, c[:cfg.max_claim_chars]))
        if len(out) >= cfg.max_claims_total:
            break
    return out


# ── Main Detector ────────────────────────────────────────────────

def detect_hallucinations(
    *,
    structured_case: Dict[str, Any],
    narrative: str,
    analysis_data: Dict[str, Any],
    documents: Optional[List[str]] = None,
    cfg: Optional[HallucinationConfig] = None,
) -> HallucinationReport:
    """
    Run hallucination detection on analysis output.

    Args:
        structured_case: The normalized StructuredCase dict
        narrative: The case narrative text
        analysis_data: The CaseAnalysisData as a dict (model_dump())
        documents: Optional list of extracted document texts
        cfg: Configuration (defaults to warn mode)

    Returns:
        HallucinationReport with ok/score/findings/stats
    """
    cfg = cfg or HallucinationConfig()

    if cfg.mode == "off":
        return HallucinationReport(
            ok=True, score=1.0, findings=[], stats={"mode": "off"}
        )

    # Build evidence index from all input sources
    evidence_index = build_evidence_index(structured_case, narrative, documents)
    log.info("Evidence index: %d items", len(evidence_index))

    findings: List[Finding] = []
    total_checked = 0
    grounded = 0

    for category, claim in _iter_claims_from_analysis(analysis_data, cfg):
        total_checked += 1
        claim_norm = norm_text(claim)

        # Skip "Unknown: …" — valid uncertainty expression
        if category == "evidence" and claim_norm.startswith("unknown"):
            grounded += 1
            continue

        # Skip generic clinical advice in next_steps
        if (cfg.allow_generic_clinical_advice
                and category in ("next_steps",)
                and is_generic_advice(claim_norm)):
            grounded += 1
            continue

        # Find matching evidence
        hits = _best_hits(claim_norm, evidence_index, cfg)
        if hits:
            grounded += 1
            continue

        # ── Ungrounded claim ──
        # Evidence and red_flags are hard errors; others are warnings
        severity = "error" if category in ("evidence", "red_flags") else "warning"
        reason = "No supporting match found in structured_case/narrative/documents."

        findings.append(Finding(
            category=category,
            severity=severity,
            claim=claim[:200],
            reason=reason,
            hits=[],
        ))

    # ── Compute groundedness score ──
    frac = (grounded / total_checked) if total_checked else 1.0
    error_count = sum(1 for f in findings if f.severity == "error")
    score = max(0.0, min(1.0, frac - 0.05 * error_count))

    # ── Strict gating ──
    ok = True
    if cfg.mode == "strict":
        if error_count > cfg.max_error_findings:
            ok = False
        if len(findings) > cfg.max_total_findings:
            ok = False

    report = HallucinationReport(
        ok=ok,
        score=round(score, 3),
        findings=findings,
        stats={
            "mode": cfg.mode,
            "total_checked": total_checked,
            "grounded": grounded,
            "findings_total": len(findings),
            "errors": error_count,
            "warnings": len(findings) - error_count,
            "evidence_index_size": len(evidence_index),
        },
    )

    log.info(
        "Hallucination report: score=%.2f, grounded=%d/%d, findings=%d (errors=%d)",
        report.score, grounded, total_checked, len(findings), error_count,
    )

    return report
