from app.schemas.schemas import StructuredCase
from app.services.llm_model import medgemma_extract_json

STRUCTURED_PROMPT = """
You are a clinical information extraction engine.

Return ONLY valid JSON matching this schema:
{
 "age": integer|null,
 "sex": string|null,
 "chief_complaint": "",
 "history_present_illness": string|null,
 "symptoms": [string],
 "timeline": {"onset": string|null,"duration": string|null,"progression": string|null},
 "exam_findings": [string],
 "abnormal_labs": [{"name": string,"value": string|null,"units": string|null,"flag": string|null}],
 "medications": [string],
 "allergies": [string],
 "comorbidities": [string],
 "family_history": [string],
 "red_flags": [string],
 "negatives": [string],
 "missing_info": [string]
}

Rules:
- JSON only. No markdown. No explanation.
- Do not invent facts.
- Use null or [] when missing.
- Striclty follow the above schema do not miss even a single attribute
"""

def narrative_to_structured_case(narrative: str) -> StructuredCase:
    prompt = STRUCTURED_PROMPT + "\n\nClinical text:\n" + narrative
    raw = medgemma_extract_json(prompt)
    return StructuredCase.model_validate(raw)
