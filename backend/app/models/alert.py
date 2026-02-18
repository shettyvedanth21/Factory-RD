from datetime import datetime
from sqlalchemy import DateTime, Boolean, ForeignKey, JSON, Enum, Text, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import Optional, Dict, Any

from .base import Base
from .rule import Severity


class Alert(Base):
    __tablename__ = "alerts"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    factory_id: Mapped[int] = mapped_column(ForeignKey("factories.id"), nullable=False)
    rule_id: Mapped[int] = mapped_column(ForeignKey("rules.id"), nullable=False)
    device_id: Mapped[int] = mapped_column(ForeignKey("devices.id"), nullable=False)
    triggered_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    resolved_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    severity: Mapped[Severity] = mapped_column(
        Enum(Severity, values_callable=lambda obj: [e.value for e in obj]),
        nullable=False
    )
    message: Mapped[Optional[str]] = mapped_column(Text)
    telemetry_snapshot: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON)
    notification_sent: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    factory: Mapped["Factory"] = relationship("Factory", back_populates="alerts")
    rule: Mapped["Rule"] = relationship("Rule", back_populates="alerts")
    device: Mapped["Device"] = relationship("Device", back_populates="alerts")

    __table_args__ = (
        Index("idx_factory_device_time", "factory_id", "device_id", "triggered_at"),
        Index("idx_factory_time", "factory_id", "triggered_at"),
        {"mysql_charset": "utf8mb4", "mysql_collate": "utf8mb4_unicode_ci"},
    )
