from pypdf import PdfReader
import app.utils.object_store as object_store
import app.models.models as model
import app.db.database as db
import io
from fastapi import HTTPException
import os
import dotenv

loadenv=()

def extract_text_from_pdf(pdf_bytes:bytes)->str:
    reader = PdfReader(io.BytesIO(pdf_bytes))
    parts = []
    for page in reader.pages:
        text = page.extract_text() or ""
        if text.strip():
            parts.append(text)
    return "\n".join(parts).strip()


def process_pdf_extraction(db_session:db, case_id:int):
    docs = (db_session.query(model.CaseFiles).filter(model.CaseFiles.case_id == case_id).all())
    for doc in docs:
        if doc.content_type != "application/pdf":
            continue

        existing = (db_session.query(model.CaseDocumentsText).filter(model.CaseDocumentsText.case_id == case_id, model.CaseDocumentsText.file_id == doc.id,model.CaseDocumentsText.extraction_method == "pypdf").first())
        if existing:
            continue
        try:
            resp  = object_store.object_store.client.get_object(Bucket = os.getenv("S3_BUCKET_NAME"),Key = doc.object_key,)
            pdf_bytes = resp['Body'].read()
            extracted_text = extract_text_from_pdf(pdf_bytes)

        except Exception as e:
            raise HTTPException(status_code = 400,detail = f"Error extracting PDF text: {str(e)}")

        case_doc_text = model.CaseDocumentsText(case_id = case_id,file_id = doc.id,extracted_text = extracted_text, extraction_method = "pypdf")
        db_session.add(case_doc_text)
        db_session.commit()
    return {"message":"PDF text extraction completed"}
