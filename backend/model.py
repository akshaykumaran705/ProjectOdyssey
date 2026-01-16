from sqlalchemy import ForeignKey, Column, Integer, String, DateTime
from sqlalchemy.sql import func
from db import Base
import datetime

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
