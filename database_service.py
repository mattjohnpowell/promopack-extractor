"""Database service functions for job tracking and audit logging."""

import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from models import AuditLog, Job, UsageStats


class DatabaseService:
    """Service for database operations."""

    @staticmethod
    async def create_job(
        session: AsyncSession,
        job_id: str,
        pdf_url: str,
        file_size: Optional[int] = None,
        page_count: Optional[int] = None,
    ) -> Job:
        """Create a new job record."""
        job = Job(
            id=job_id,
            pdf_url=pdf_url,
            file_size=file_size,
            page_count=page_count,
        )
        session.add(job)
        await session.commit()
        await session.refresh(job)
        return job

    @staticmethod
    async def update_job_status(
        session: AsyncSession,
        job_id: str,
        status: str,
        result: Optional[Dict] = None,
        error_message: Optional[str] = None,
        processing_time: Optional[int] = None,
    ) -> Optional[Job]:
        """Update job status and result."""
        job = await session.get(Job, job_id)
        if not job:
            return None

        job.status = status
        job.updated_at = datetime.utcnow()

        if status in ["completed", "failed"]:
            job.completed_at = datetime.utcnow()

        if result:
            job.result = json.dumps(result)

        if error_message:
            job.error_message = error_message

        if processing_time:
            job.processing_time = processing_time

        await session.commit()
        await session.refresh(job)
        return job

    @staticmethod
    async def get_job(session: AsyncSession, job_id: str) -> Optional[Job]:
        """Get job by ID."""
        return await session.get(Job, job_id)

    @staticmethod
    async def log_request(
        session: AsyncSession,
        request_id: str,
        endpoint: str,
        method: str,
        status_code: int,
        client_ip: Optional[str] = None,
        user_agent: Optional[str] = None,
        processing_time: Optional[int] = None,
        error_message: Optional[str] = None,
        pdf_url: Optional[str] = None,
        file_size: Optional[int] = None,
    ):
        """Log an API request."""
        log_entry = AuditLog(
            request_id=request_id,
            endpoint=endpoint,
            method=method,
            status_code=status_code,
            client_ip=client_ip,
            user_agent=user_agent,
            processing_time=processing_time,
            error_message=error_message,
            pdf_url=pdf_url,
            file_size=file_size,
        )
        session.add(log_entry)
        await session.commit()

    @staticmethod
    async def update_usage_stats(
        session: AsyncSession,
        endpoint: str,
        processing_time: int,
        is_error: bool = False,
        file_size: Optional[int] = None,
    ):
        """Update usage statistics for the current day."""
        today = datetime.utcnow().date()

        # Get or create usage stats for today
        stmt = select(UsageStats).where(
            UsageStats.date >= datetime.combine(today, datetime.min.time()),
            UsageStats.date < datetime.combine(today, datetime.max.time()),
            UsageStats.endpoint == endpoint,
        )
        result = await session.execute(stmt)
        stats = result.scalar_one_or_none()

        if not stats:
            stats = UsageStats(
                date=datetime.utcnow(),
                endpoint=endpoint,
                request_count=0,
                total_processing_time=0,
                error_count=0,
            )
            session.add(stats)

        stats.request_count += 1
        stats.total_processing_time += processing_time

        if is_error:
            stats.error_count += 1

        if file_size is not None:
            # Simple average calculation (in production, use more sophisticated method)
            if stats.avg_file_size is not None:
                stats.avg_file_size = (stats.avg_file_size + file_size) // 2
            else:
                stats.avg_file_size = file_size

        await session.commit()

    @staticmethod
    async def get_usage_stats(
        session: AsyncSession, days: int = 30
    ) -> List[Dict]:
        """Get usage statistics for the last N days."""
        cutoff_date = datetime.utcnow() - timedelta(days=days)

        stmt = select(
            UsageStats.date,
            UsageStats.endpoint,
            UsageStats.request_count,
            UsageStats.total_processing_time,
            UsageStats.error_count,
            UsageStats.avg_file_size,
        ).where(UsageStats.date >= cutoff_date)

        result = await session.execute(stmt)

        stats = []
        for row in result:
            stats.append({
                "date": row.date.isoformat(),
                "endpoint": row.endpoint,
                "request_count": row.request_count,
                "total_processing_time": row.total_processing_time,
                "error_count": row.error_count,
                "avg_file_size": row.avg_file_size,
            })

        return stats

    @staticmethod
    async def cleanup_old_data(session: AsyncSession, days_to_keep: int = 90):
        """Clean up old audit logs and jobs."""
        cutoff_date = datetime.utcnow() - timedelta(days=days_to_keep)

        # Delete old audit logs
        stmt1 = delete(AuditLog).where(AuditLog.timestamp < cutoff_date)
        await session.execute(stmt1)

        # Delete old completed/failed jobs (keep recent ones)
        stmt2 = delete(Job).where(
            Job.status.in_(["completed", "failed"]),
            Job.created_at < cutoff_date
        )
        await session.execute(stmt2)

        await session.commit()