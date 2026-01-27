import requests, json, re

MLX_URL = "http://127.0.0.1:8080"

def _extract_json(text: str) -> str:
    import re
    m = re.search(r"\{.*\}", text, re.S)
    if not m:
        raise ValueError("No JSON object found")
    return m.group(0)

def medgemma_chat(prompt: str) -> str:
    payload = {
        "model": "mlx-community/medgemma-4b-it-4bit",  # name doesn't matter for local usually
        "messages": [
            {"role": "system", "content": "You output JSON only."},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.0,
        "max_tokens": 1200
    }

    r = requests.post(
        f"{MLX_URL}/chat/completions",
        json=payload,
        timeout=180
    )
    r.raise_for_status()
    return r.json()["choices"][0]["message"]["content"]

def medgemma_extract_json(prompt: str) -> dict:
    output = medgemma_chat(prompt)
    try:
        json_str = _extract_json(output)
        return json.loads(json_str)
    except Exception:
        repair_prompt = f"""
You returned an invalid response.

Return ONLY valid JSON. No markdown. No extra words.

Here is your previous output:
{output}

Now return the corrected JSON only.
""".strip()
        output2 = medgemma_chat(repair_prompt)
        json_str2 = _extract_json(output2)
        return json.loads(json_str2)
