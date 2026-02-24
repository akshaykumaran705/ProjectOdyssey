from typing import Optional, List, Dict, Any, Literal
from datetime import datetime, timezone
from pydantic import BaseModel, Field, ConfigDict


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


# -------------------------
# Request schemas
# -------------------------
class UserCreate(BaseModel):
    email: str
    password: str
    role: str
    # IMPORTANT: generally do NOT accept created_at from client
    # remove this field entirely for request models
    # created_at: datetime = Field(default_factory=now_utc)


class UserLogin(BaseModel):
    email: str
    password: str


class CaseCreate(BaseModel):
    title: str
    chief_complaint: str
    history_present_illness: Optional[str] = None
    age: Optional[int] = None
    sex: Optional[str] = None


class CaseFileCreate(BaseModel):
    case_id: int
    file_name: str
    content_type: str
    object_key: str
    size_bytes: int


class AuditLogCreate(BaseModel):
    user_id: int
    case_id: Optional[int] = None
    action: str
    meta_data: Dict[str, Any] = Field(default_factory=dict)


# -------------------------
# Response schemas
# -------------------------
class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    role: str
    created_at: datetime


class CaseResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_by_user_id: int
    title: str
    chief_complaint: str
    history_present_illness: Optional[str] = None
    age: Optional[int] = None
    sex: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class CaseFileResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    case_id: int
    file_name: str
    content_type: str
    object_key: str
    size_bytes: int
    created_at: datetime


class AuditLogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    case_id: Optional[int] = None
    action: str
    meta_data: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime


# -------------------------
# Structured case schema
# -------------------------
class Timeline(BaseModel):
    onset: Optional[str] = None
    duration: Optional[str] = None
    progression: Optional[str] = None


class AbnormalLabs(BaseModel):
    name: str
    value: Optional[str] = None
    units: Optional[str] = None
    flag: Optional[str] = None


class StructuredCase(BaseModel):
    age: Optional[int] = None
    sex: Optional[str] = None
    chief_complaint: str = ""
    history_present_illness: Optional[str] = None

    symptoms: List[str] = Field(default_factory=list)
    timeline: Timeline = Field(default_factory=Timeline)

    exam_findings: List[str] = Field(default_factory=list)
    abnormal_labs: List[AbnormalLabs] = Field(default_factory=list)

    medications: List[str] = Field(default_factory=list)
    allergies: List[str] = Field(default_factory=list)
    comorbidities: List[str] = Field(default_factory=list)
    family_history: List[str] = Field(default_factory=list)

    red_flags: List[str] = Field(default_factory=list)
    negatives: List[str] = Field(default_factory=list)
    missing_info: List[str] = Field(default_factory=list)

Confidence = str
CareSetting = str

class InputHashes(BaseModel):
    structred_source_hash: str
    narrative_hash:str

class AnalysisMeta(BaseModel):
    prompt_version:str
    model_id:Optional[str]= None
    latency_ms: Optional[str]=None
    grounding_failures: Optional[int] = None
    calibrations_applied: Optional[int] = None
    evidence_linked: Optional[int] = None
    safety_escalated: Optional[bool] = None

class EvidenceItem(BaseModel):
    claim:str
    support:List[str] = Field(default_factory=list)
    against:List[str] = Field(default_factory=list)

class DxItem(BaseModel):
    name:str
    rank:Optional[int] = None
    confidence:Optional[Confidence] = None
    probability_estimate:Optional[float]=Field(default=None,ge=0,le=1)
    rationale:Optional[str] = None
    key_evidence:Any = None
    red_flags:List[str] = Field(default_factory=list)
    rule_in:List[str] = Field(default_factory=list)
    rule_out:List[str]= Field(default_factory=list)

class NextStep(BaseModel):
    category:str
    priority:str
    action:str
    rationale:str

class SafetyNet(BaseModel):
    return_precautions: Any
    escalation_triggers: Any

class CaseAnalysisData(BaseModel):
    schema_version: str = "case_analysis_v1"
    summary:Optional[str] = None
    top_differentials:List[DxItem] = Field(default_factory=list)
    recommended_next_steps:Any = Field(default_factory=list)
    missing_info:List[str] = Field(default_factory=list)
    contradiction_or_quality_issues :List[str] = Field(default_factory=list)
    care_setting_recommendation:Optional[CareSetting] = None
    safety_net: Any = Field(default_factory=dict)
    limitations:Optional[str] = None
    meta: Optional[AnalysisMeta] = None
    input_hashes: Optional[InputHashes] = None

class CaseAnalysisOut(BaseModel):
    case_id:int
    source_hash:str
    analysis_version:str
    analysis_data:CaseAnalysisData
    created_at:datetime

class AnalyzeRequest(BaseModel):
    force:bool = False
    analysis_version:str = "v1"
    max_differentials:int = Field(default=8,ge=3,le=13)
    include_probabilities:bool = False