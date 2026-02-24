"""
Evidence Index — builds a searchable, flattened list of evidence strings
with provenance tracking from all input sources.

Sources:
  - structured_case → paths like "abnormal_labs[2].name"
  - narrative → sentence-level splits
  - documents → optional extracted doc text chunks
"""
from dataclasses import dataclass
from typing import Any, Dict, List, Literal, Optional, Tuple

from .normalize import norm_text

Source = Literal["structured", "narrative", "document"]


@dataclass(frozen=True)
class EvidenceItem:
    source: Source
    path: Optional[str]
    raw: str
    norm: str


def _flatten_structured(obj: Any, prefix: str = "") -> List[Tuple[str, str]]:
    """
    Recursively flatten a nested dict/list into (path, string_value) pairs.
    Only strings and primitive values become evidence strings.
    """
    out: List[Tuple[str, str]] = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            p = f"{prefix}.{k}" if prefix else str(k)
            out.extend(_flatten_structured(v, p))
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            p = f"{prefix}[{i}]"
            out.extend(_flatten_structured(v, p))
    else:
        if obj is None:
            return out
        s = str(obj).strip()
        if s:
            out.append((prefix, s))
    return out


def build_evidence_index(
    structured_case: Dict[str, Any],
    narrative: str,
    documents: Optional[List[str]] = None,
) -> List[EvidenceItem]:
    """Build the master evidence index from all input sources."""
    items: List[EvidenceItem] = []

    # ── Structured case ──
    for path, val in _flatten_structured(structured_case):
        items.append(EvidenceItem(
            source="structured", path=path, raw=val, norm=norm_text(val)
        ))

    # ── Narrative (full + sentence-level splits) ──
    if narrative:
        items.append(EvidenceItem(
            source="narrative", path=None, raw=narrative, norm=norm_text(narrative)
        ))
        # Split on sentence boundaries
        for part in narrative.split("."):
            part = part.strip()
            if len(part) > 3:
                items.append(EvidenceItem(
                    source="narrative", path=None, raw=part, norm=norm_text(part)
                ))

    # ── Documents (optional) ──
    if documents:
        for idx, doc in enumerate(documents):
            if not doc:
                continue
            items.append(EvidenceItem(
                source="document", path=f"documents[{idx}]",
                raw=doc, norm=norm_text(doc)
            ))
            for part in doc.split("."):
                part = part.strip()
                if len(part) > 3:
                    items.append(EvidenceItem(
                        source="document", path=f"documents[{idx}]",
                        raw=part, norm=norm_text(part)
                    ))

    return items
