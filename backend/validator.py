from schema import CaseAnalysisData
def enforce_analysis_rules(data:CaseAnalysisData)->None:
    for dx in data.top_differentials:
        if len(dx.key_evidence.support)<2:
            raise ValueError(f"DX'{dx.name}' has <2 supporting facts")
        if len(dx.key_evidence.against)<1:
            raise ValueError(f"DX '{dx.name}' missing against_or_unknown")
        
        any_low_med = any(dx.confidence in ("low","medium") for dx in data.top_differentials)
        if any_low_med and len(data.missing_info)<5:
            raise ValueError("missin_information must have >=5 items when any dx has low/medium confidence")
        
        if data.care_setting_recommendation == "ED_now":
            has_start_triage = any(s.category == "triage" and s.priority=="stat" for s in data.recommended_next_steps)
            if not has_start_triage:
                raise ValueError("ED_now requires at least one triage step with priority 'stat'")