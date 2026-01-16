from pydantic import BaseModel, Field
import datetime
from typing import Optional

# Request schemas (for creating/updating)
class UserCreate(BaseModel):
    email: str
    password: str
    role: str
    created_at: datetime.datetime = Field(default_factory=datetime.datetime.utcnow)

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
    content_type: str
    object_key: str
    size_bytes: int

class AuditLogCreate(BaseModel):
    user_id: int
    case_id: int
    action: str
    meta_data: str  # Fixed: match model.py field name

# Response schemas (for reading)
class UserResponse(BaseModel):
    id: int
    email: str
    role: str
    created_at: datetime.datetime
    
    class Config:
        from_attributes = True

class CaseResponse(BaseModel):
    id: int
    created_by_user_id: int
    title: str
    chief_complaint: str
    history_present_illness: Optional[str] = None
    age: Optional[int] = None
    sex: Optional[str] = None
    created_at: datetime.datetime
    updated_at: datetime.datetime
    
    class Config:
        from_attributes = True

class CaseFileResponse(BaseModel):
    id: int
    case_id: int
    content_type: str
    object_key: str
    size_bytes: int
    created_at: datetime.datetime
    
    class Config:
        from_attributes = True

class AuditLogResponse(BaseModel):
    id: int
    user_id: int
    case_id: int
    action: str
    meta_data: str
    created_at: datetime.datetime
    
    class Config:
        from_attributes = True

# Legacy models (keeping for backward compatibility if needed)
class Users(UserCreate):
    created_at: datetime.datetime = Field(default_factory=datetime.datetime.utcnow)

class Cases(CaseCreate):
    created_by_user_id: int
    created_at: datetime.datetime = Field(default_factory=datetime.datetime.utcnow)
    updated_at: datetime.datetime = Field(default_factory=datetime.datetime.utcnow)

class CaseFiles(CaseFileCreate):
    created_at: datetime.datetime = Field(default_factory=datetime.datetime.utcnow)

class AuditLogs(AuditLogCreate):
    created_at: datetime.datetime = Field(default_factory=datetime.datetime.utcnow)

class Token(BaseModel):
    access_token: str
    token_type: str

exported_models = [Users, Cases, CaseFiles, AuditLogs]
