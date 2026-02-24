"""
Cost Engine — deterministic, no LLM required.

Extracts recommended tests from analysis_data, normalizes names,
looks up catalog prices, computes totals. Unmapped tests get $0
with a "No pricing in catalog" note.
"""
import logging
from typing import Any

from app.schemas.schema_phase5 import CostEstimate, CostLineItem
from app.services.cost_catalog import normalize_test_name, lookup

log = logging.getLogger(__name__)


def _extract_test_items(analysis_data: dict, structured_case: dict) -> list[str]:
    """
    Collect all candidate test/action items from the analysis.
    Sources:
      1. recommended_next_steps[*].action (if category is diagnostic/test-like)
      2. top_differentials[*].confirmatory_tests (if present)
      3. top_differentials[*].key_evidence.attributed_evidence[*] (only tests)
      4. structured_case.missing_info (tests only)
    """
    raw_items: list[str] = []

    # 1. Recommended next steps
    steps = analysis_data.get("recommended_next_steps", [])
    if isinstance(steps, list):
        for step in steps:
            if isinstance(step, dict):
                cat = (step.get("category") or "").lower()
                action = step.get("action", "")
                # Include if it looks like a test/diagnostic
                if any(kw in cat for kw in ("diagnostic", "lab", "imaging", "test", "workup")):
                    raw_items.append(action)
                elif any(kw in action.lower() for kw in (
                    "obtain", "order", "check", "measure", "draw", "perform",
                    "send", "collect", "schedule", "repeat",
                )):
                    raw_items.append(action)

    # 2. Missing info from structured case (often tests)
    for mi in structured_case.get("missing_info", []):
        if isinstance(mi, str) and len(mi) > 2:
            raw_items.append(mi)

    return raw_items


def _deduplicate(items: list[str]) -> list[str]:
    """Deduplicate by normalized test name."""
    seen: set[str] = set()
    out: list[str] = []
    for item in items:
        key = normalize_test_name(item)
        if key not in seen:
            seen.add(key)
            out.append(item)
    return out


def compute_cost_estimate(
    analysis_data: dict,
    structured_case: dict,
) -> CostEstimate:
    """
    Build a deterministic CostEstimate from analysis data.
    NO LLM needed — pure catalog lookup.
    """
    raw_items = _extract_test_items(analysis_data, structured_case)
    items = _deduplicate(raw_items)

    line_items: list[CostLineItem] = []
    low_total = 0.0
    high_total = 0.0
    unknown_count = 0

    for item_name in items:
        result = lookup(item_name)
        if result:
            entry, norm_key = result
            li = CostLineItem(
                item=norm_key,
                cpt_or_code=entry.get("code"),
                low=entry["low"],
                high=entry["high"],
            )
            low_total += entry["low"]
            high_total += entry["high"]
        else:
            # Unmapped: include with $0 and a note
            norm_key = normalize_test_name(item_name)
            li = CostLineItem(
                item=norm_key if norm_key != item_name.lower().strip() else item_name,
                cpt_or_code=None,
                low=0.0,
                high=0.0,
                notes="No pricing in catalog — cost unknown",
            )
            unknown_count += 1

        line_items.append(li)

    # Build assumptions
    assumptions = [
        "Prices are US cash-pay estimates without insurance",
        "Costs vary significantly by facility and region",
        "Professional fees (interpretation) may be billed separately",
        "Emergency/urgent pricing may be higher",
    ]
    if unknown_count > 0:
        assumptions.append(
            f"{unknown_count} item(s) not in catalog — excluded from total"
        )

    exclusions = [
        "Insurance copays/coinsurance not reflected",
        "Specialist consultation fees not included",
        "Medication costs not included",
        "Facility fees may apply in addition to test costs",
    ]

    # Determine confidence
    if unknown_count == 0 and len(line_items) > 0:
        confidence = "high"
    elif unknown_count <= 2:
        confidence = "medium"
    else:
        confidence = "low"

    estimate = CostEstimate(
        low_total=round(low_total, 2),
        high_total=round(high_total, 2),
        line_items=line_items,
        assumptions=assumptions,
        exclusions=exclusions,
        confidence=confidence,
    )

    log.info(
        "Cost estimate: %d items, $%.0f–$%.0f, %d unknown",
        len(line_items), low_total, high_total, unknown_count,
    )

    return estimate
