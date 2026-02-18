from datetime import datetime
from enum import Enum as PyEnum
from sqlalchemy import String, DateTime, ForeignKey, JSON, Enum, Text, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import Optional, Dict, Any, List

from .base import Base


class JobType(PyEnum):
    ANOMALY = "anomaly"
    FAILURE_PREDICTION = "failure_prediction"
    ENERGY_FORECAST = "energy_forecast"
    AI_COPILOT = "ai_copilot"


class JobMode(PyEnum):
    STANDARD = "standard"
    AI_COPILOT = "ai_copilot"


class JobStatus(PyEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETE = "complete"
    FAILED = "failed"


class AnalyticsJob(Base):
    __tablename__ = "analytics_jobs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)  # UUID
    factory_id: Mapped[int] = mapped_column(ForeignKey("factories.id"), nullable=False)
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    job_type: Mapped[JobType] = mapped_column(
        Enum(JobType, values_callable=lambda obj: [e.value for e in obj]),
        nullable=False
    )
    mode: Mapped[JobMode] = mapped_column(
        Enum(JobMode, values_callable=lambda obj: [e.value for e in obj]),
        default=JobMode.STANDARD
    )
    device_ids: Mapped[List[int]] = mapped_column(JSON, nullable=False)
    date_range_start: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    date_range_end: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    status: Mapped[JobStatus] = mapped_column(
        Enum(JobStatus, values_callable=lambda obj: [e.value for e in obj]),
        default=JobStatus.PENDING
    )
    result_url: Mapped[Optional[str]] = mapped_column(String(500))
    error_message: Mapped[Optional[str]] = mapped_column(Text)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    factory: Mapped["Factory"] = relationship("Factory", back_populates="analytics_jobs")

    __table_args__ = (
        Index("idx_factory_status", "factory_id", "status"),
        {"mysql_charset": "utf8mb4", "mysql_collate": "utf8mb4_unicode_ci"},
    )
