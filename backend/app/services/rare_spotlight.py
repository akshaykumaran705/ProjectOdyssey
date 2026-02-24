"""
Rare Disease Spotlight Engine — LLM-driven with guardrails.

Uses the same MedGemma model to identify potential rare disease candidates
from the structured case + analysis data, then validates evidence grounding.
"""
import json
import logging
import time
from typing import Optional

import requests

from app.schemas.schema_phase5 import RareSpotlight, RareCandidate
from hallucination.normalize import norm_text

log = logging.getLogger(__name__)

RARE_SYSTEM_PROMPT = """You are a rare disease screening assistant.
Given a clinical case, identify potential rare disease diagnoses that
might be missed by standard evaluation. Focus on conditions with
diagnostic delay risk.

OUTPUT: valid JSON only. No markdown. No commentary.""".strip()

RARE_USER_PROMPT = """
StructuredCase:
{structured_case_json}

Analysis (differentials already identified):
{analysis_summary}

Based on the findings above, identify up to 3 rare disease candidates
that may be missed. For each candidate, explain:
- why it fits the presentation
- what evidence supports it (from the case data only)
- what evidence is missing
- what confirmatory tests to order
- which specialist to refer to

Return a JSON object:
{{
  "candidates": [
    {{
      "name": "disease name",
      "likelihood": "high" or "medium" or "low",
      "why_this_fits": ["reason1", "reason2"],
      "supporting_evidence": ["finding from case"],
      "missing_evidence": ["what would strengthen"],
      "confirmatory_tests": ["test1", "test2"],
      "specialist_referral": "specialty",
      "safety_notes": ["urgent warning if any"]
    }}
  ],
  "diagnostic_delay_risk": 0-100,
  "delay_reasoning": ["reason1"],
  "next_best_actions": ["action1"]
}}

Max 3 candidates. Only use findings from the case. Output ONLY JSON.
""".strip()


def _extract_json(text: str) -> dict:
    """Pull JSON from LLM response."""
    import re
    s = text.strip()
    # Strip code fences
    m = re.search(r"```(?:json)?\s*(.*?)\s*```", s, re.DOTALL)
    if m:
        s = m.group(1).strip()
    # Find first {
    start = s.find("{")
    if start == -1:
        raise ValueError("No JSON object found")
    s = s[start:]
    for end in range(len(s), 0, -1):
        try:
            return json.loads(s[:end])
        except json.JSONDecodeError:
            continue
    raise ValueError("Could not parse JSON")


def _validate_evidence(
    candidates: list[dict],
    structured_case: dict,
    narrative: str,
) -> list[dict]:
    """
    Evidence integrity check: move ungrounded supporting_evidence to missing_evidence.
    """
    input_blob = (json.dumps(structured_case, default=str) + " " + narrative).lower()

    for cand in candidates:
        grounded = []
        ungrounded = []
        for ev in cand.get("supporting_evidence", []):
            ev_norm = norm_text(ev)
            if len(ev_norm) < 4 or ev_norm in input_blob:
                grounded.append(ev)
            else:
                # Check word overlap
                ev_words = set(ev_norm.split())
                overlap = sum(1 for w in ev_words if w in input_blob)
                if len(ev_words) > 0 and overlap / len(ev_words) >= 0.6:
                    grounded.append(ev)
                else:
                    ungrounded.append(ev)

        cand["supporting_evidence"] = grounded
        existing_missing = cand.get("missing_evidence", [])
        cand["missing_evidence"] = existing_missing + [
            f"[ungrounded] {ev}" for ev in ungrounded
        ]

    return candidates


def compute_rare_spotlight(
    structured_case: dict,
    analysis_data: dict,
    narrative: str,
    *,
    base_url: str = "http://localhost:8080",
    model: str = "mlx-community/medgemma-4b-it-4bit",
) -> RareSpotlight:
    """
    Run the rare disease spotlight engine.
    LLM-driven with evidence grounding guardrails.
    """
    # Build analysis summary for the prompt
    dxs = analysis_data.get("top_differentials", [])
    summary_parts = []
    for dx in dxs[:3]:
        name = dx.get("name", "?")
        conf = dx.get("confidence", "?")
        summary_parts.append(f"- {name} (confidence: {conf})")
    analysis_summary = "\n".join(summary_parts) if summary_parts else "No differentials identified."

    # Truncate structured case for context window
    sc_json = json.dumps(structured_case, default=str)
    if len(sc_json) > 2000:
        sc_json = sc_json[:2000] + "..."

    user_prompt = RARE_USER_PROMPT.format(
        structured_case_json=sc_json,
        analysis_summary=analysis_summary,
    )

    payload = {
        "model": model,
        "max_tokens": 800,
        "temperature": 0.2,
        "messages": [
            {"role": "system", "content": RARE_SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
    }

    t0 = time.time()
    try:
        r = requests.post(
            f"{base_url.rstrip('/')}/chat/completions",
            json=payload,
            timeout=120,
        )
        r.raise_for_status()
        content = r.json()["choices"][0]["message"]["content"]
        latency_ms = int((time.time() - t0) * 1000)
        log.info("Rare spotlight LLM: %d chars in %dms", len(content), latency_ms)
    except Exception as exc:
        log.error("Rare spotlight LLM failed: %s", exc)
        return RareSpotlight(
            candidates=[],
            diagnostic_delay_risk=0,
            delay_reasoning=["LLM call failed — retry recommended"],
            next_best_actions=[],
        )

    # Parse response
    try:
        raw = _extract_json(content)
    except ValueError as e:
        log.warning("Rare spotlight JSON parse failed: %s", e)
        return RareSpotlight(
            candidates=[],
            diagnostic_delay_risk=0,
            delay_reasoning=[f"LLM output unparseable: {e}"],
        )

    # Extract candidates and validate evidence
    raw_candidates = raw.get("candidates", [])
    validated_candidates = _validate_evidence(raw_candidates, structured_case, narrative)

    # Build validated RareCandidates
    candidates = []
    for c in validated_candidates[:3]:
        try:
            rc = RareCandidate(
                name=c.get("name", "Unknown"),
                likelihood=c.get("likelihood", "low"),
                why_this_fits=c.get("why_this_fits", []),
                supporting_evidence=c.get("supporting_evidence", []),
                missing_evidence=c.get("missing_evidence", []),
                confirmatory_tests=c.get("confirmatory_tests", []),
                specialist_referral=c.get("specialist_referral"),
                safety_notes=c.get("safety_notes", []),
            )
            candidates.append(rc)
        except Exception as e:
            log.warning("Skipping invalid rare candidate: %s", e)

    # Build delay risk
    delay_risk = raw.get("diagnostic_delay_risk", 0)
    if not isinstance(delay_risk, int):
        try:
            delay_risk = int(delay_risk)
        except (ValueError, TypeError):
            delay_risk = 0
    delay_risk = max(0, min(100, delay_risk))

    return RareSpotlight(
        candidates=candidates,
        diagnostic_delay_risk=delay_risk,
        delay_reasoning=raw.get("delay_reasoning", []),
        next_best_actions=raw.get("next_best_actions", []),
    )
