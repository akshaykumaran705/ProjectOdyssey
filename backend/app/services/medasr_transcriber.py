"""
MedASR Transcriber — audio-to-text for clinical dictation.

Uses OpenAI Whisper (via the local `whisper` Python package) for
offline transcription. Falls back gracefully if model not available.

Production constraints:
  - Sanitize transcript (strip control chars, normalize whitespace)
  - Deterministic output (temperature=0)
  - Store transcript hash for caching
"""
import hashlib
import io
import logging
import re
import tempfile
import os

log = logging.getLogger(__name__)

_WS = re.compile(r"\s+")
_CTRL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f]")


def _sanitize(text: str) -> str:
    """Remove control characters, normalize whitespace."""
    text = _CTRL.sub("", text)
    text = _WS.sub(" ", text).strip()
    return text


def compute_audio_hash(audio_bytes: bytes) -> str:
    """SHA-256 hash of audio file bytes."""
    return hashlib.sha256(audio_bytes).hexdigest()


def transcribe_audio_bytes(audio_bytes: bytes, model_size: str = "base") -> dict:
    """
    Transcribe audio bytes using Whisper.

    Returns:
        {"text": str, "model": str, "method": str}
    """
    try:
        import whisper
    except ImportError:
        log.warning("Whisper not installed — using placeholder transcription")
        return {
            "text": "[Audio transcription unavailable — whisper package not installed]",
            "model": "none",
            "method": "placeholder",
        }

    # Write to temp file (whisper needs file path)
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        tmp.write(audio_bytes)
        tmp_path = tmp.name

    try:
        model = whisper.load_model(model_size)
        result = model.transcribe(tmp_path, temperature=0, language="en")
        raw_text = result.get("text", "")
        clean = _sanitize(raw_text)
        return {
            "text": clean,
            "model": f"whisper-{model_size}",
            "method": "whisper",
        }
    except Exception as e:
        log.error("Whisper transcription failed: %s", e)
        return {
            "text": f"[Transcription failed: {e}]",
            "model": f"whisper-{model_size}",
            "method": "whisper_error",
        }
    finally:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
