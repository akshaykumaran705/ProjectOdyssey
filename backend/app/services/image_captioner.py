"""
Image Captioner — extracts clinical findings from medical images.

Uses the local MedGemma vision model (via MLX-VLM server) to generate
structured clinical captions/findings from uploaded images.
"""
import base64
import hashlib
import logging
import re

import requests

log = logging.getLogger(__name__)


def compute_image_hash(image_bytes: bytes) -> str:
    """SHA-256 hash of image file bytes."""
    return hashlib.sha256(image_bytes).hexdigest()


CAPTION_PROMPT = """You are a clinical imaging assistant.
Describe the clinically relevant findings in this medical image.
Use the format:
Findings: [structured description]
Impression: [one-line clinical assessment]

Be factual. If uncertain, state uncertainty. Output text only, no JSON.""".strip()


def caption_image_bytes(
    image_bytes: bytes,
    content_type: str = "image/jpeg",
    *,
    base_url: str = "http://localhost:8080",
    model: str = "mlx-community/medgemma-4b-it-4bit",
) -> dict:
    """
    Generate clinical caption/findings for a medical image.

    Returns:
        {"text": str, "model": str, "method": str}
    """
    # Encode image as base64 data URL
    b64 = base64.b64encode(image_bytes).decode("utf-8")
    mime = content_type or "image/jpeg"
    data_url = f"data:{mime};base64,{b64}"

    payload = {
        "model": model,
        "max_tokens": 400,
        "temperature": 0.1,
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "image_url", "image_url": {"url": data_url}},
                    {"type": "text", "text": CAPTION_PROMPT},
                ],
            }
        ],
    }

    try:
        r = requests.post(
            f"{base_url.rstrip('/')}/chat/completions",
            json=payload,
            timeout=120,
        )
        r.raise_for_status()
        content = r.json()["choices"][0]["message"]["content"]
        clean = content.strip()
        log.info("Image caption: %d chars", len(clean))
        return {
            "text": clean,
            "model": model,
            "method": "medgemma_vision",
        }
    except Exception as e:
        log.error("Image captioning failed: %s", e)
        return {
            "text": f"[Image captioning failed: {e}]",
            "model": model,
            "method": "medgemma_vision_error",
        }
