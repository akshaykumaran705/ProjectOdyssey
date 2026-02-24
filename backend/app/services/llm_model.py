"""
Low-level LLM chat wrapper for the local MLX inference server.
Used by structured_case.py for the normalize step.
"""
import json
import logging
import re

import requests

log = logging.getLogger(__name__)

import os
MLX_URL = os.getenv("LLM_BASE_URL", "http://127.0.0.1:8080")
MAX_PROMPT_CHARS = 2500  # keep prompt short to avoid context overflow on 4B model

_JSON_OBJ_RE = re.compile(r"\{.*\}", re.S)


def _extract_json(text: str) -> str:
    m = _JSON_OBJ_RE.search(text)
    if not m:
        raise ValueError("No JSON object found in LLM response")
    return m.group(0)


def medgemma_chat(prompt: str) -> str:
    # Truncate prompt if too long
    if len(prompt) > MAX_PROMPT_CHARS:
        prompt = prompt[:MAX_PROMPT_CHARS] + "\n... [truncated]"

    payload = {
        "model": "mlx-community/medgemma-4b-it-4bit",
        "messages": [
            {"role": "system", "content": "You output JSON only. Be concise."},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.1,
        "max_tokens": 800,
    }

    r = requests.post(f"{MLX_URL}/chat/completions", json=payload, timeout=120)
    r.raise_for_status()
    return r.json()["choices"][0]["message"]["content"]


def medgemma_extract_json(prompt: str) -> dict:
    output = medgemma_chat(prompt)
    try:
        json_str = _extract_json(output)
        return json.loads(json_str)
    except Exception as e1:
        log.warning("JSON extraction attempt 1 failed: %s", e1)
        # retry with repair prompt
        repair_prompt = (
            "You returned an invalid response.\n"
            "Return ONLY valid JSON. No markdown. No extra words.\n\n"
            f"Here is your previous output:\n{output[:500]}\n\n"
            "Now return the corrected JSON only."
        )
        try:
            output2 = medgemma_chat(repair_prompt)
            json_str2 = _extract_json(output2)
            return json.loads(json_str2)
        except Exception as e2:
            log.error("JSON extraction attempt 2 also failed: %s", e2)
            # Return a minimal valid dict so normalize doesn't 500
            return {
                "age": None,
                "sex": None,
                "chief_complaint": "Could not extract – LLM produced invalid output",
                "symptoms": [],
                "timeline": {},
                "exam_findings": [],
                "abnormal_labs": [],
                "medications": [],
                "allergies": [],
                "comorbidities": [],
                "family_history": [],
                "red_flags": [],
                "negatives": [],
                "missing_info": ["Full extraction failed – please retry or use a larger model"],
            }
