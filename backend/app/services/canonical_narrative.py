"""
Canonical Narrative Builder — merges all modalities into one unified narrative.

Assembles:
  1. Case fields (age, sex, CC, HPI)
  2. Extracted PDF text (from CaseDocumentsText)
  3. Audio transcript blocks (from CaseAudioTranscripts)
  4. Image findings blocks (from CaseImageFindings)

This unified narrative is what gets passed to normalization + analysis.
"""
from typing import List
import app.models.models as model


def build_canonical_narrative(
    case: model.Cases,
    extracted_documents: List[model.CaseDocumentsText],
    transcripts: List[model.CaseAudioTranscript] | None = None,
    image_findings: List[model.CaseImageFinding] | None = None,
) -> str:
    """
    Build a single canonical narrative from all available data sources.
    """
    sections = []

    # ── 1. Patient Story (Structured Fields) ──
    sections.append("=== Patient Story (Structured) ===")
    sections.append(f"Age: {case.age if case.age is not None else 'Unknown'}")
    sections.append(f"Sex: {case.sex if case.sex else 'Unknown'}")
    sections.append(f"Chief Complaint: {case.chief_complaint.strip() if case.chief_complaint else 'Not provided'}")
    hpi = case.history_present_illness.strip() if case.history_present_illness else "Not provided"
    sections.append(f"History of Present Illness: {hpi}")
    sections.append("")

    # ── 2. Uploaded Documents (Extracted Text) ──
    sections.append("=== Uploaded Documents (Extracted Text) ===")
    if not extracted_documents:
        sections.append("No clinical documents were provided.")
    else:
        for idx, doc in enumerate(extracted_documents, start=1):
            doc_text = (doc.extracted_text or "").strip()
            if not doc_text:
                doc_text = "[No readable text extracted from this document]"
            sections.append(f"[Document {idx} - File ID: {doc.file_id}]")
            sections.append(doc_text)
            sections.append("")
    sections.append("")

    # ── 3. Dictated Audio Transcripts (MedASR) ──
    if transcripts:
        sections.append("=== Dictated Audio Transcript (MedASR) ===")
        for idx, tx in enumerate(transcripts, start=1):
            txt = (tx.transcript_text or "").strip()
            if txt:
                method = tx.extraction_method or "unknown"
                sections.append(f"[Audio {idx} - Method: {method}]")
                sections.append(txt)
                sections.append("")
        sections.append("")

    # ── 4. Image Findings (Caption) ──
    if image_findings:
        sections.append("=== Image Findings (Clinical Caption) ===")
        for idx, img in enumerate(image_findings, start=1):
            txt = (img.caption_text or "").strip()
            if txt:
                method = img.extraction_method or "unknown"
                sections.append(f"[Image {idx} - Method: {method}]")
                sections.append(txt)
                sections.append("")
        sections.append("")

    sections.append("END OF CASE")
    return "\n".join(sections)
