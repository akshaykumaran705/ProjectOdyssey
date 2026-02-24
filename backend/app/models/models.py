from sqlalchemy import ForeignKey, Column, Integer, String, DateTime,Text
from sqlalchemy.sql import func
from sqlalchemy import UniqueConstraint
from app.db.database import Base
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
    narrative_text = Column(Text, nullable=True)
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


class AnalysisLog(Base):
    __tablename__ = "analysis_logs"
    id = Column(Integer, primary_key=True)
    case_id = Column(Integer, ForeignKey("cases.id", ondelete="CASCADE"), index=True, nullable=False)
    analysis_id = Column(Integer, ForeignKey("case_analysis.id", ondelete="SET NULL"), nullable=True)
    model_id = Column(String, nullable=True)
    prompt_version = Column(String, nullable=True)
    latency_ms = Column(Integer, nullable=True)
    cache_hit = Column(Integer, default=0)  # 0=false, 1=true (SQLite compat)
    repair_attempts = Column(Integer, default=0)
    calibrations_applied = Column(Integer, default=0)
    evidence_linked = Column(Integer, default=0)
    hallucinations_found = Column(Integer, default=0)
    safety_escalated = Column(Integer, default=0)  # 0=false, 1=true
    validation_warnings = Column(JSONB, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)


class CaseRareSpotlight(Base):
    __tablename__ = "case_rare_spotlight"
    id = Column(Integer, primary_key=True)
    case_id = Column(Integer, ForeignKey("cases.id", ondelete="CASCADE"), unique=True, nullable=False)
    spotlight_data = Column(JSONB, nullable=False)
    source_hash = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)


class CaseCostEstimate(Base):
    __tablename__ = "case_cost_estimates"
    id = Column(Integer, primary_key=True)
    case_id = Column(Integer, ForeignKey("cases.id", ondelete="CASCADE"), unique=True, nullable=False)
    estimate_data = Column(JSONB, nullable=False)
    source_hash = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)


class CaseTrustReport(Base):
    __tablename__ = "case_trust_reports"
    id = Column(Integer, primary_key=True)
    case_id = Column(Integer, ForeignKey("cases.id", ondelete="CASCADE"), unique=True, nullable=False)
    trust_data = Column(JSONB, nullable=False)
    source_hash = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)


class CaseAudioFile(Base):
    __tablename__ = "case_audio_files"
    id = Column(Integer, primary_key=True)
    case_id = Column(Integer, ForeignKey("cases.id", ondelete="CASCADE"), nullable=False)
    file_name = Column(String, nullable=True)
    object_key = Column(String, nullable=False)
    content_type = Column(String, nullable=True)
    size_bytes = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)


class CaseAudioTranscript(Base):
    __tablename__ = "case_audio_transcripts"
    id = Column(Integer, primary_key=True)
    case_id = Column(Integer, ForeignKey("cases.id", ondelete="CASCADE"), nullable=False)
    audio_file_id = Column(Integer, ForeignKey("case_audio_files.id", ondelete="CASCADE"), nullable=True)
    transcript_text = Column(String, nullable=False)
    extraction_method = Column(String, default="whisper")
    model_name = Column(String, nullable=True)
    source_hash = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)


class CaseImageFinding(Base):
    __tablename__ = "case_image_findings"
    id = Column(Integer, primary_key=True)
    case_id = Column(Integer, ForeignKey("cases.id", ondelete="CASCADE"), nullable=False)
    file_id = Column(Integer, ForeignKey("case_files.id", ondelete="CASCADE"), nullable=True)
    caption_text = Column(String, nullable=False)
    extraction_method = Column(String, default="medgemma_vision")
    model_name = Column(String, nullable=True)
    source_hash = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)


class CaseJob(Base):
    __tablename__ = "case_jobs"
    id = Column(Integer, primary_key=True)
    case_id = Column(Integer, ForeignKey("cases.id", ondelete="CASCADE"), nullable=False)
    job_type = Column(String, nullable=False)  # extract, transcribe, caption, normalize, analyze, ingest_all
    status = Column(String, default="pending")  # pending, running, complete, failed
    started_at = Column(DateTime, nullable=True)
    finished_at = Column(DateTime, nullable=True)
    error_message = Column(String, nullable=True)
    meta_data = Column(JSONB, nullable=True)  # latency, counts, etc.
    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)
