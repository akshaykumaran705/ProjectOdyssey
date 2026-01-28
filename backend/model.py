from sqlalchemy import ForeignKey, Column, Integer, String, DateTime,Text
from sqlalchemy.sql import func
from sqlalchemy import UniqueConstraint
from db import Base
import datetime
from sqlalchemy.dialects.postgresql import JSONB

class Users(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    password = Column(String)
    role = Column(String)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

class Cases(Base):
    __tablename__ = 'cases'
    id = Column(Integer, primary_key=True, index=True)
    created_by_user_id = Column(Integer, ForeignKey('users.id'))
    title = Column(String)
    chief_complaint = Column(String)
    history_present_illness = Column(String, nullable=True)
    age = Column(Integer, nullable=True)
    sex = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

class CaseFiles(Base):
    __tablename__ = 'case_files'
    id = Column(Integer, primary_key=True, index=True)
    case_id = Column(Integer, ForeignKey('cases.id'))
    file_name = Column(String)
    content_type = Column(String)
    object_key = Column(String)
    size_bytes = Column(Integer)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

class AuditLogs(Base):
    __tablename__ = 'audit_logs'
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    case_id = Column(Integer, ForeignKey('cases.id'))
    action = Column(String)
    meta_data = Column(String)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
class CaseDocumentsText(Base):
    __tablename__ = "case_documents_text"
    id = Column(Integer,primary_key=True,index = True)
    case_id = Column(Integer,ForeignKey("cases.id"))
    file_id = Column(Integer,ForeignKey("case_files.id"))
    extracted_text = Column(Text,nullable=False)
    extraction_method = Column(String)
    #created_at = Column(DateTime,default = datetime.datetime.utcnow)

class CaseStructured(Base):
    __tablename__ = "case_structured"
    id = Column(Integer,primary_key = True,index = True)
    case_id = Column(Integer,ForeignKey("cases.id"))
    normalized_data = Column(JSONB,nullable=False)
    source_hash = Column(String)
    created_at = Column(DateTime,default = datetime.datetime.utcnow)
    #updated_at = Column(DateTime,default = datetime.datetime.utcnow,onupdate=datetime.datetime.utcnow)

class CaseAnalysis(Base):
    __tablename__ = "case_analysis"
    id = Column(Integer,primary_key=True)
    case_id = Column(Integer,ForeignKey("cases.id",ondelete="CASCADE"),index=True,nullable=False)
    source_hash = Column(Text,nullable=False)
    analysis_version = Column(Text,nullable=False,default="v1")
    analysis_data = Column(JSONB,nullable=False)
    created_at = Column(DateTime,default=datetime.datetime.utcnow,nullable=False)
    __table_args__ = (
        UniqueConstraint("case_id","source_hash","analysis_version",name="uq_case_analysis_case_hash_version"),
    )


