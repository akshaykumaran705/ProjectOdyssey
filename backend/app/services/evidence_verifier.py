"""
Evidence Verifier — checks every claim in the analysis against
the evidence index. Produces EvidenceLink objects per diagnosis.

Adapted to ProjectOdyssey's CaseAnalysisData schema:
  - DxItem.key_evidence can be list, dict, or attributed_evidence
  - DxItem.rationale is Optional[str]
"""
import logging
from typing import Any

from app.schemas.schema_trust import EvidenceLink, DiagnosisTrust
from app.services.evidence_index import build_evidence_index, check_claim

log = logging.getLogger(__name__)


def _extract_claims(key_evidence: Any) -> list[str]:
    """Pull all evidence strings from key_evidence (any shape)."""
    claims: list[str] = []

    if key_evidence is None:
        return claims

    if isinstance(key_evidence, list):
        for item in key_evidence:
            if isinstance(item, str):
                claims.append(item)
            elif isinstance(item, dict):
                claims.append(item.get("text", str(item)))

    elif isinstance(key_evidence, dict):
        for key, val in key_evidence.items():
            if isinstance(val, list):
                for item in val:
                    if isinstance(item, str):
                        claims.append(item)
                    elif isinstance(item, dict):
                        claims.append(item.get("text", str(item)))
            elif isinstance(val, str):
                claims.append(val)

    return [c for c in claims if c and len(c.strip()) > 2]


def verify_analysis(
    analysis_data: dict,
    structured_case: dict,
    narrative: str = "",
) -> list[DiagnosisTrust]:
    """
    Verify every evidence claim in the analysis against the case data.
    Returns a DiagnosisTrust for each differential.
    """
    evidence_map = build_evidence_index(structured_case, narrative)
    results: list[DiagnosisTrust] = []

    for dx in analysis_data.get("top_differentials", []):
        dx_name = dx.get("name", "Unknown")
        key_ev = dx.get("key_evidence")
        claims = _extract_claims(key_ev)

        links: list[EvidenceLink] = []
        supported_count = 0

        for claim in claims:
            # Skip "Unknown: ..." markers
            if claim.lower().startswith("unknown"):
                links.append(EvidenceLink(
                    claim=claim, supported=True,
                    reason="Acknowledged uncertainty marker",
                ))
                supported_count += 1
                continue

            is_supported, source_path, excerpt = check_claim(claim, evidence_map)

            links.append(EvidenceLink(
                claim=claim,
                supported=is_supported,
                source_path=source_path,
                source_excerpt=excerpt,
                reason=None if is_supported else "Claim not found in structured case or narrative",
            ))

            if is_supported:
                supported_count += 1

        total = len(claims)
        ratio = (supported_count / total) if total > 0 else 1.0

        results.append(DiagnosisTrust(
            diagnosis=dx_name,
            evidence_links=links,
            support_ratio=round(ratio, 3),
        ))

    log.info(
        "Evidence verifier: %d diagnoses, avg support ratio %.2f",
        len(results),
        sum(r.support_ratio for r in results) / max(len(results), 1),
    )

    return results
