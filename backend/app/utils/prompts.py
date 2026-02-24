PROMPT_VERSION = "analysis_version_v1.2"

SYSTEM_PROMPT_V1_1 = """
You are a clinical reasoning assistant.
Use ONLY the facts provided. If something is missing, say "Unknown".
NEVER invent facts.

OUTPUT: valid JSON only. No markdown, no commentary.
Be concise. Keep arrays short (max 3-5 items each).
""".strip()

USER_PROMPT_V1_1 = """
StructuredCase JSON:
{structured_case_json}

Narrative:
{narrative_text}

Return a JSON object with these exact keys:
{{
  "summary": "one paragraph case summary",
  "top_differentials": [
    {{
      "name": "diagnosis name",
      "confidence": "high or medium or low",
      "key_evidence": ["evidence1", "evidence2"],
      "red_flags": []
    }}
  ],
  "recommended_next_steps": [
    {{
      "category": "Diagnostics",
      "priority": "stat",
      "action": "what to do",
      "rationale": "why"
    }}
  ],
  "missing_info": ["item1"],
  "care_setting_recommendation": "ED_now or urgent_care_24h or outpatient_routine",
  "safety_net": {{
    "return_precautions": [],
    "escalation_triggers": []
  }},
  "limitations": "text"
}}

Max 3 differentials. Output ONLY the JSON object, nothing else.
"""
