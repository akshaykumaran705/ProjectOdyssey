from typing import Optional, List, Dict, Any
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
    chief_complaint: str
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
