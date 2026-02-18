from datetime import datetime
from sqlalchemy import String, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import Optional, List

from .base import Base


class Factory(Base):
    __tablename__ = "factories"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    timezone: Mapped[str] = mapped_column(String(100), default="UTC")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    users: Mapped[List["User"]] = relationship("User", back_populates="factory")
    devices: Mapped[List["Device"]] = relationship("Device", back_populates="factory")
    rules: Mapped[List["Rule"]] = relationship("Rule", back_populates="factory")
    alerts: Mapped[List["Alert"]] = relationship("Alert", back_populates="factory")
    analytics_jobs: Mapped[List["AnalyticsJob"]] = relationship("AnalyticsJob", back_populates="factory")
    reports: Mapped[List["Report"]] = relationship("Report", back_populates="factory")
