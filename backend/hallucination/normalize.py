"""
Text normalization utilities for stable matching despite casing,
punctuation, units, and whitespace differences.
"""
import re

_WS = re.compile(r"\s+")
_PUNCT = re.compile(r"[^\w\s\.\+\-/%]")  # keep lab-relevant symbols
_NUM = re.compile(r"(?<!\w)(\d+(\.\d+)?)(?!\w)")


def norm_text(s: str) -> str:
    """Normalize text for comparison: lowercase, strip punctuation, collapse whitespace."""
    s = (s or "").strip().lower()
    s = _PUNCT.sub(" ", s)
    s = _WS.sub(" ", s).strip()
    return s


def extract_numbers(s: str) -> list[str]:
    """Extract all numeric values from a string (e.g., '0.45', '160', '98.6')."""
    return [m.group(1) for m in _NUM.finditer(s or "")]
