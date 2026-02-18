from datetime import datetime
from enum import Enum as PyEnum
from sqlalchemy import String, DateTime, Boolean, ForeignKey, JSON, Enum, Integer, Text, Index, Table, Column
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import Optional, Dict, Any, List

from .base import Base


class RuleScope(PyEnum):
    DEVICE = "device"
    GLOBAL = "global"


class ScheduleType(PyEnum):
    ALWAYS = "always"
    TIME_WINDOW = "time_window"
    DATE_RANGE = "date_range"


class Severity(PyEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


# Association table for Rule-Device many-to-many relationship
rule_devices = Table(
    "rule_devices",
    Base.metadata,
    Column("rule_id", Integer, ForeignKey("rules.id", ondelete="CASCADE"), primary_key=True),
    Column("device_id", Integer, ForeignKey("devices.id", ondelete="CASCADE"), primary_key=True),
)


class Rule(Base):
    __tablename__ = "rules"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    factory_id: Mapped[int] = mapped_column(ForeignKey("factories.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    scope: Mapped[RuleScope] = mapped_column(
        Enum(RuleScope, values_callable=lambda obj: [e.value for e in obj]),
        nullable=False,
        default=RuleScope.DEVICE
    )
    conditions: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=False)
    cooldown_minutes: Mapped[Optional[int]] = mapped_column(Integer, default=15)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    schedule_type: Mapped[ScheduleType] = mapped_column(
        Enum(ScheduleType, values_callable=lambda obj: [e.value for e in obj]),
        default=ScheduleType.ALWAYS
    )
    schedule_config: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON)
    severity: Mapped[Severity] = mapped_column(
        Enum(Severity, values_callable=lambda obj: [e.value for e in obj]),
        default=Severity.MEDIUM
    )
    notification_channels: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON)
    created_by: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    factory: Mapped["Factory"] = relationship("Factory", back_populates="rules")
    devices: Mapped[List["Device"]] = relationship("Device", secondary=rule_devices)
    alerts: Mapped[List["Alert"]] = relationship("Alert", back_populates="rule")

    __table_args__ = (
        Index("idx_factory_active", "factory_id", "is_active"),
        {"mysql_charset": "utf8mb4", "mysql_collate": "utf8mb4_unicode_ci"},
    )


class RuleCooldown(Base):
    __tablename__ = "rule_cooldowns"

    rule_id: Mapped[int] = mapped_column(ForeignKey("rules.id", ondelete="CASCADE"), primary_key=True)
    device_id: Mapped[int] = mapped_column(ForeignKey("devices.id", ondelete="CASCADE"), primary_key=True)
    last_triggered: Mapped[datetime] = mapped_column(DateTime, nullable=False)
