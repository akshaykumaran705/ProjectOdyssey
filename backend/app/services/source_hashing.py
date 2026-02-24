"""
Source hashing — deterministic content-based hashes for all modalities.

Includes case fields, extracted documents, audio transcripts, and image captions
so any new data triggers re-normalization cleanly.
"""
import hashlib
import json
from typing import List, Dict, Any


def compute_source_hash(
    case_fields: Dict[str, Any],
    extracted_docs: List[Dict[str, Any]],
    schema_version: str = "structuredcase_v1",
    transcripts: List[str] | None = None,
    image_captions: List[str] | None = None,
) -> str:
    """
    Compute SHA-256 hash of all case input data.

    Includes case fields, documents, audio transcripts, and image captions
    so any modality change triggers re-normalization.
    """
    normalized_case = {
        k: (v.strip() if isinstance(v, str) else v)
        for k, v in case_fields.items()
    }

    normalized_docs = []
    for d in extracted_docs:
        normalized_docs.append({
            "file_id": d.get("file_id"),
            "extracted_text": (d.get("extracted_text") or ""),
        })
    normalized_docs.sort(key=lambda x: (x["file_id"] is None, x["file_id"]))

    payload = {
        "schema_version": schema_version,
        "case": normalized_case,
        "documents": normalized_docs,
    }

    # Phase 7: include audio transcripts and image captions
    if transcripts:
        payload["transcripts"] = sorted(transcripts)
    if image_captions:
        payload["image_captions"] = sorted(image_captions)

    canonical = json.dumps(payload, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()