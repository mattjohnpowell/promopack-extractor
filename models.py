"""Database models for job tracking and audit logs."""

from datetime import datetime
from typing import Optional

from sqlalchemy import Column, DateTime, Integer, String, Text
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class Job(Base):
    """Model for tracking async jobs."""

    __tablename__ = "jobs"

    id = Column(String, primary_key=True, index=True)
    status = Column(String, nullable=False, default="pending")  # pending, processing, completed, failed
    pdf_url = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    error_message = Column(Text, nullable=True)
    result = Column(Text, nullable=True)  # JSON string of extracted claims
    processing_time = Column(Integer, nullable=True)  # in seconds
    file_size = Column(Integer, nullable=True)  # in bytes
    page_count = Column(Integer, nullable=True)


class AuditLog(Base):
    """Model for audit logging."""

    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    request_id = Column(String, index=True)
    user_id = Column(String, nullable=True)  # For future user authentication
    endpoint = Column(String, nullable=False)
    method = Column(String, nullable=False)
    status_code = Column(Integer, nullable=False)
    client_ip = Column(String, nullable=True)
    user_agent = Column(String, nullable=True)
    processing_time = Column(Integer, nullable=True)  # in milliseconds
    error_message = Column(Text, nullable=True)
    pdf_url = Column(String, nullable=True)  # For PDF processing requests
    file_size = Column(Integer, nullable=True)


class UsageStats(Base):
    """Model for usage analytics."""

    __tablename__ = "usage_stats"

    id = Column(Integer, primary_key=True, autoincrement=True)
    date = Column(DateTime, default=datetime.utcnow, index=True)
    endpoint = Column(String, nullable=False)
    request_count = Column(Integer, default=0)
    total_processing_time = Column(Integer, default=0)  # in milliseconds
    error_count = Column(Integer, default=0)
    avg_file_size = Column(Integer, nullable=True)  # in bytes