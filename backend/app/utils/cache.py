import hashlib, json

def stable_hash(obj:dict)->str:
    blob = json.dumps(obj,sort_keys=True,separators=(",",":")).encode('utf-8')
    return hashlib.sha256(blob).hexdigest()

def compute_analysis_source_hash(*,structured_source_hash:str,narrative:str,analysis_version:str)->str:
    payload = {
        "structured_source_hash": structured_source_hash,
        "narrative": narrative,
        "analysis_version":analysis_version,
    }
    return stable_hash(payload)

def compute_narrative_hash(narrative:str) -> str:
    return stable_hash({"narrative":narrative})
