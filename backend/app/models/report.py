from datetime import datetime
from enum import Enum as PyEnum
from sqlalchemy import String, DateTime, Boolean, ForeignKey, JSON, Enum, Text, BigInteger
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import Optional, List

from .base import Base


class ReportFormat(PyEnum):
    PDF = "pdf"
    EXCEL = "excel"
    JSON = "json"


class ReportStatus(PyEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETE = "complete"
    FAILED = "failed"


class Report(Base):
    __tablename__ = "reports"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)  # UUID
    factory_id: Mapped[int] = mapped_column(ForeignKey("factories.id"), nullable=False)
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    title: Mapped[Optional[str]] = mapped_column(String(255))
    device_ids: Mapped[List[int]] = mapped_column(JSON, nullable=False)
    date_range_start: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    date_range_end: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    format: Mapped[ReportFormat] = mapped_column(
        Enum(ReportFormat, values_callable=lambda obj: [e.value for e in obj]),
        nullable=False
    )
    include_analytics: Mapped[bool] = mapped_column(Boolean, default=False)
    analytics_job_id: Mapped[Optional[str]] = mapped_column(String(36))
    status: Mapped[ReportStatus] = mapped_column(
        Enum(ReportStatus, values_callable=lambda obj: [e.value for e in obj]),
        default=ReportStatus.PENDING
    )
    file_url: Mapped[Optional[str]] = mapped_column(String(500))
    file_size_bytes: Mapped[Optional[int]] = mapped_column(BigInteger)
    error_message: Mapped[Optional[str]] = mapped_column(Text)
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    factory: Mapped["Factory"] = relationship("Factory", back_populates="reports")

    __table_args__ = (
        {"mysql_charset": "utf8mb4", "mysql_collate": "utf8mb4_unicode_ci"},
    )
