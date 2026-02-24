"""
LLM Runner – sends structured case + narrative to a local MLX inference server
and robustly parses the response into CaseAnalysisData.

Key hardening measures for small (4B) models:
  * Narrative is truncated to MAX_NARRATIVE_CHARS to avoid context overflow.
  * Two extraction attempts with an automatic fix-prompt retry.
  * If both attempts fail, returns a *minimal* CaseAnalysisData so the API
    never 500s – the user sees a partial result they can re-run.
"""
import json
import logging
import re
import time

import requests

from app.schemas.schemas import CaseAnalysisData
from app.utils.prompts import SYSTEM_PROMPT_V1_1, USER_PROMPT_V1_1

log = logging.getLogger(__name__)

MAX_NARRATIVE_CHARS = 2000          # prevent context-window overflow on 4B models
_JSON_BLOCK_RE = re.compile(r"```(?:json)?\s*(.*?)\s*```", re.DOTALL | re.IGNORECASE)


# ── JSON extraction ──────────────────────────────────────────────
def extract_json_string(text: str) -> str:
    """Pull the first valid JSON object/array out of *text*.  Raises ValueError."""
    if not text:
        raise ValueError("Empty LLM response")

    s = text.strip()

    # 1) fenced code block
    m = _JSON_BLOCK_RE.search(s)
    if m:
        s = m.group(1).strip()

    if s.startswith("{") or s.startswith("["):
        # fast path – try the whole thing first
        try:
            json.loads(s)
            return s
        except json.JSONDecodeError:
            pass

    # 2) locate first { or [
    starts = [i for i in (s.find("{"), s.find("[")) if i != -1]
    if not starts:
        raise ValueError("No JSON object/array start found in response")
    start = min(starts)

    tail = s[start:]
    # try progressively shrinking from end
    for end in range(len(tail), 0, -1):
        chunk = tail[:end].strip()
        try:
            json.loads(chunk)
            return chunk
        except Exception:
            continue

    raise ValueError("Could not extract valid JSON from response")


# ── Fallback builder ─────────────────────────────────────────────
def _build_fallback(narrative: str, error_msg: str) -> CaseAnalysisData:
    """Return a minimal CaseAnalysisData so the API never 500s."""
    return CaseAnalysisData(
        summary=f"Analysis could not be completed by the local LLM. Error: {error_msg}",
        top_differentials=[],
        recommended_next_steps=[],
        missing_info=["Full LLM analysis failed – please retry or use a larger model"],
        care_setting_recommendation="outpatient_routine",
        safety_net={"return_precautions": [], "escalation_triggers": []},
        limitations="The local 4-billion-parameter model was unable to generate valid JSON for this case.",
    )


FIX_PROMPT = """\
Your previous JSON had this error:
{error}

Return ONLY corrected, valid JSON (no markdown, no code fences).
Keep it concise – max 3 differentials, short evidence arrays.
"""


# ── Runner ────────────────────────────────────────────────────────
class LLMRunner:
    def __init__(self, base_url: str, model: str):
        self.base_url = base_url.rstrip("/")
        self.model = model

    def analyze(
        self,
        structured_case: dict,
        narrative: str,
        *,
        max_differentials: int,
        include_probabilities: bool,
    ):
        # Truncate narrative to avoid overwhelming the small model
        if len(narrative) > MAX_NARRATIVE_CHARS:
            narrative = narrative[:MAX_NARRATIVE_CHARS] + "\n... [truncated]"

        user_prompt = USER_PROMPT_V1_1.format(
            structured_case_json=structured_case,
            narrative_text=narrative,
        )

        payload = {
            "model": self.model,
            "max_tokens": 800,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT_V1_1},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0.1,
        }

        t0 = time.time()

        # ── attempt 1 ──
        try:
            r = requests.post(
                f"{self.base_url}/chat/completions", json=payload, timeout=120
            )
            r.raise_for_status()
        except Exception as exc:
            log.error("LLM request failed: %s", exc)
            return _build_fallback(narrative, str(exc)), 0

        dt_ms = int((time.time() - t0) * 1000)
        content = r.json()["choices"][0]["message"]["content"]
        log.info("LLM attempt-1 length: %d chars", len(content))
        print("=== LLM RAW OUTPUT (attempt 1) ===")
        print(content[:500])
        print("=== END ===")

        try:
            json_str = extract_json_string(content)
            data = CaseAnalysisData.model_validate_json(json_str)
            return data, dt_ms
        except Exception as e1:
            log.warning("Attempt-1 parse failed: %s", e1)

        # ── attempt 2 (fix prompt) ──
        try:
            payload["messages"].append({"role": "assistant", "content": content})
            payload["messages"].append(
                {"role": "user", "content": FIX_PROMPT.format(error=str(e1))}
            )
            r2 = requests.post(
                f"{self.base_url}/chat/completions", json=payload, timeout=120
            )
            r2.raise_for_status()
            content2 = r2.json()["choices"][0]["message"]["content"]
            log.info("LLM attempt-2 length: %d chars", len(content2))
            print("=== LLM RAW OUTPUT (attempt 2) ===")
            print(content2[:500])
            print("=== END ===")
            json_str2 = extract_json_string(content2)
            data2 = CaseAnalysisData.model_validate_json(json_str2)
            return data2, dt_ms
        except Exception as e2:
            log.error("Attempt-2 also failed: %s – returning fallback", e2)
            return _build_fallback(narrative, f"Attempt1: {e1} | Attempt2: {e2}"), dt_ms