from sqlalchemy.orm import Session
from model import CaseAnalysis
def get_case_analysis(db:Session,case_id:int,source_hash:str,analysis_version:str):
    return(db.query(CaseAnalysis).filter(CaseAnalysis.case_id==case_id,CaseAnalysis.source_hash == source_hash,CaseAnalysis.analysis_version==analysis_version).first())

def get_latest_case_analysis(db:Session,case_id:int,analysis_version:str):
    return (db.query(CaseAnalysis).filter(CaseAnalysis.analysis_version == analysis_version).order_by(CaseAnalysis.created_at.desc())).first()

def create_case_analysis(db:Session,*, case_id:int, source_hash:str,analysis_version:str,analysis_data:dict,model_id:str|None=None,latency_ms:int|None=None):
    obj = CaseAnalysis(case_id=case_id,source_hash=source_hash,analysis_version=analysis_version,analysis_data=analysis_data,model_id=model_id,latency_ms=latency_ms)
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj

