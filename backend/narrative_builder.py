from typing import List
import model 
def build_case_narrative(case:model.Cases, extracted_documents:List[model.CaseDocumentsText])->str:
    sections = []
    demographics = f""" Age:{case.age if case.age is not None else "Unknown"}
                    Sex: {case.sex if case.sex else "Unknown"}
"""
    sections.append(demographics.strip())
    chief_complaint_block = f"""{case.chief_complaint.strip() if case.chief_complaint else "Not provided"}
"""
    sections.append(chief_complaint_block.strip())
    hpi_block = f"""{case.history_present_illness.strip() if case.history_present_illness else "Not Provided"}
"""
    sections.append(hpi_block.strip())
    docs_section = ["Uploaded Clinical Documents"]
    if not extracted_documents:
        docs_section.append("No clinical documents were provided")
    else:
        for idx, doc in enumerate(extracted_documents,start=1):
            doc_text = (doc.extracted_text or "").strip()

            if not doc_text:
                doc_text = "[No readble text extracted from this doc]"
            
            docs_section.append(f"""Document{idx} Source file id: {doc.file_id} {doc_text}""".strip())
            sections.append("\n".join(docs_section))
            sections.append("END OF CASE")
            narrative = "\n\n".join(sections)
            return narrative