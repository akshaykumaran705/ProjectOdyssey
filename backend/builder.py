from sqlalchemy.orm import Session
from case_analysis import get_case_analysis,create_case_analysis
from cache import compute_analysis_source_hash
from runner import LLMRunner
from prompts import PROMPT_VERSION
from validator import enforce_analysis_rules
from cache import compute_narrative_hash

def generate_case_analysis(db:Session,*,case_id:int,structured_source_hash:str,structured_case:dict,narrative:str,analysis_version:str,force:bool,runner:LLMRunner):
    narrative_hash = compute_narrative_hash(narrative)

    source_hash = compute_analysis_source_hash(structured_source_hash=structured_source_hash,narrative=narrative,analysis_version=analysis_version)

    if not force:
        existing = get_case_analysis(db,case_id,source_hash,analysis_version)
        if existing:
            return existing,True
        
    analysis_data,latency_ms = runner.analyze(structured_case=structured_case,narrative=narrative,max_differentials=8,include_probabilities=False)
    analysis_data.meta.model_id = runner.model
    analysis_data.meta.latency_ms = latency_ms
    analysis_data.meta.prompt_version = PROMPT_VERSION
    analysis_data.input_hashes.structured_source_hash = structured_source_hash
    analysis_data.input_hashes.narrative_hash = narrative_hash
    enforce_analysis_rules(analysis_data)

    created = create_case_analysis(db,case_id=case_id,source_hash=source_hash,analysis_version=analysis_version,analysis_data=analysis_data.model_dump(),model_id=runner.model,latency_ms=latency_ms)
    return created,False
