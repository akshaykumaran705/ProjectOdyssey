"""
Evidence Indexer — builds a searchable ground truth map from the case data.

Input: structured_case dict + narrative string
Output: evidence_map dict[normalized_phrase → list of source paths]

This is the foundation of the anti-hallucination firewall.
"""
import re
from typing import Any

_WS = re.compile(r"\s+")
_PUNCT = re.compile(r"[^\w\s\.\+\-/%]")

# ── Medical Aliases ──
ALIASES: dict[str, list[str]] = {
    "shortness of breath": ["sob", "dyspnea", "difficulty breathing"],
    "oxygen saturation": ["spo2", "o2 sat", "pulse ox"],
    "chest pain": ["cp", "chest discomfort", "substernal pain"],
    "blood pressure": ["bp", "hypertension", "htn"],
    "heart rate": ["hr", "pulse", "tachycardia", "bradycardia"],
    "respiratory rate": ["rr", "tachypnea"],
    "temperature": ["temp", "fever", "febrile", "hypothermia"],
    "white blood cell": ["wbc", "leukocytosis", "leukopenia"],
    "hemoglobin": ["hgb", "hb", "anemia"],
    "platelets": ["plt", "thrombocytopenia", "thrombocytosis"],
    "potassium": ["k", "k+", "hyperkalemia", "hypokalemia"],
    "sodium": ["na", "na+", "hypernatremia", "hyponatremia"],
    "creatinine": ["cr", "cre", "renal function"],
    "troponin": ["trop", "troponin i", "troponin t", "cardiac enzymes"],
    "brain natriuretic peptide": ["bnp", "nt-probnp", "pro-bnp"],
    "antinuclear antibody": ["ana"],
    "complement": ["c3", "c4", "complement c3 c4"],
    "electrocardiogram": ["ecg", "ekg", "12 lead"],
}

# Build reverse alias map
_REVERSE_ALIASES: dict[str, str] = {}
for canonical, aliases in ALIASES.items():
    for alias in aliases:
        _REVERSE_ALIASES[alias] = canonical


def _normalize(text: str) -> str:
    """Normalize text for matching."""
    s = (text or "").strip().lower()
    s = _PUNCT.sub(" ", s)
    s = _WS.sub(" ", s).strip()
    return s


def _flatten(obj: Any, prefix: str = "") -> list[tuple[str, str]]:
    """Recursively flatten a dict/list into (path, string_value) pairs."""
    out: list[tuple[str, str]] = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            p = f"{prefix}.{k}" if prefix else str(k)
            out.extend(_flatten(v, p))
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            out.extend(_flatten(v, f"{prefix}[{i}]"))
    elif obj is not None:
        s = str(obj).strip()
        if s:
            out.append((prefix, s))
    return out


def build_evidence_index(
    structured_case: dict,
    narrative: str = "",
) -> dict[str, list[str]]:
    """
    Build a map: normalized_phrase → [source_path, ...].

    Each structured value becomes an entry.
    Aliases are expanded so "SOB" matches "shortness of breath".
    Narrative sentences are also indexed.
    """
    evidence_map: dict[str, list[str]] = {}

    def _add(phrase: str, path: str):
        norm = _normalize(phrase)
        if len(norm) < 2:
            return
        evidence_map.setdefault(norm, [])
        if path not in evidence_map[norm]:
            evidence_map[norm].append(path)
        # Also add individual significant words (3+ chars)
        for word in norm.split():
            if len(word) >= 3:
                evidence_map.setdefault(word, [])
                if path not in evidence_map[word]:
                    evidence_map[word].append(path)

    # Index structured case
    for path, val in _flatten(structured_case, "structured_case"):
        _add(val, path)
        # Also try canonical aliases
        val_norm = _normalize(val)
        canonical = _REVERSE_ALIASES.get(val_norm)
        if canonical:
            _add(canonical, path)

    # Index narrative sentences
    if narrative:
        for part in narrative.split("."):
            part = part.strip()
            if len(part) > 3:
                _add(part, "narrative")

    return evidence_map


def check_claim(claim: str, evidence_map: dict[str, list[str]]) -> tuple[bool, str | None, str | None]:
    """
    Check if a claim is supported by the evidence index.

    Returns (supported, source_path, source_excerpt).
    Uses: exact substring → token overlap → alias expansion
    """
    claim_norm = _normalize(claim)
    if not claim_norm:
        return True, None, None

    # 1. Exact match in evidence map
    if claim_norm in evidence_map:
        paths = evidence_map[claim_norm]
        return True, paths[0], claim_norm

    # 2. Check if claim is substring of any evidence key
    for key, paths in evidence_map.items():
        if claim_norm in key or key in claim_norm:
            return True, paths[0], key

    # 3. Token overlap: if ≥70% of claim tokens appear in evidence
    claim_tokens = set(claim_norm.split())
    if not claim_tokens:
        return True, None, None

    best_overlap = 0.0
    best_path = None
    best_key = None
    for key, paths in evidence_map.items():
        key_tokens = set(key.split())
        overlap = len(claim_tokens & key_tokens)
        ratio = overlap / len(claim_tokens) if claim_tokens else 0
        if ratio > best_overlap:
            best_overlap = ratio
            best_path = paths[0]
            best_key = key

    if best_overlap >= 0.7:
        return True, best_path, best_key

    # 4. Alias expansion
    canonical = _REVERSE_ALIASES.get(claim_norm)
    if canonical and canonical in evidence_map:
        return True, evidence_map[canonical][0], canonical

    return False, None, None
