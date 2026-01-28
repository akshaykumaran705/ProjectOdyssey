import time, requests
from schema import CaseAnalysisData
from prompts import SYSTEM_PROMPT_V1_1,USER_PROMPT_V1_1
import json
import re
from typing import Any
_JSON_BLOCK_RE = re.compile(r"```(?:json)?\s*(.*?)\s*```", re.DOTALL | re.IGNORECASE)

def extract_json_string(text: str) -> str:
    """
    Extract JSON from:
    - ```json ... ```
    - plain JSON
    - extra commentary before/after JSON
    Returns a JSON string that starts with { or [.
    Raises ValueError if not found.
    """
    if not text:
        raise ValueError("Empty LLM response")

    s = text.strip()

    # Case 1: fenced block
    m = _JSON_BLOCK_RE.search(s)
    if m:
        s = m.group(1).strip()

    # If it's already valid JSON, return directly
    if s.startswith("{") or s.startswith("["):
        return s

    # Case 2: find first JSON object/array in the text
    start_candidates = [i for i in (s.find("{"), s.find("[")) if i != -1]
    if not start_candidates:
        raise ValueError("No JSON object/array start found in response")
    start = min(start_candidates)

    # Try progressively shrinking from end until json.loads works (cheap + effective)
    tail = s[start:]
    for end in range(len(tail), 0, -1):
        chunk = tail[:end].strip()
        try:
            json.loads(chunk)
            return chunk
        except Exception:
            continue

    raise ValueError("Could not extract valid JSON from response")

class LLMRunner:
    def __init__(self,base_url:str,model:str):
        self.base_url = base_url.rstrip("/")
        self.model = model
    
    def analyze(self,structured_case:dict,narrative:str,*,max_differentials:int,include_probabilities:bool):
        user_prompt = USER_PROMPT_V1_1.format(structured_case_json = structured_case,narrative_text=narrative)

        payload = {
            "model":self.model,
            "max_tokens":2000,
            "messages":[
                {"role":"system","content":SYSTEM_PROMPT_V1_1},
                {"role":"user","content":user_prompt}
            ],
            "temperature":0.0,
        }

        t0 = time.time()
        r = requests.post(f"{self.base_url}/chat/completions",json=payload,timeout=180)
        r.raise_for_status()
        dt_ms = int((time.time()-t0)*1000)
        content = r.json()["choices"][0]["message"]["content"]
        print("=== LLM RAW OUTPUT (attempt 1) ===")
        print(content)
        print("=== END ===")
        try:
            json_str_1 = extract_json_string(content)
            data = CaseAnalysisData.model_validate_json(json_str_1)
            return data,dt_ms
        except Exception as e:
            payload["messages"].append({"role":"assistant","content":content})
            payload["messages"].append({"role":"user","content":FIX_PROMPT})
            r2 = requests.post(f"{self.base_url}/chat/completions",json=payload,timeout=120)
            content2 = r2.json()["choices"][0]["message"]["content"]
            print("=== LLM RAW OUTPUT (attempt 2) ===")
            print(content2)
            print("=== END ===")
            json_str_2 = extract_json_string(content2)
            data2 = CaseAnalysisData.model_validate_json(json_str_2)
            return data2,dt_ms
    
FIX_PROMPT = """
Your previous JSON failed validation with this error:
{error}

Return a corrected JSON that matches the schema and satisfies:
- each dx >=2 support, >=1 against_or_unknown
- if any low/medium confidence => missing_information >=5
- if ED_now => include triage stat step
No extra keys, output only JSON.
Your last response was not valid raw JSON for the schema.
Return ONLY valid JSON (no markdown, no code fences), matching the schema exactly.

"""