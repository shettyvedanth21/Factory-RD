from datetime import datetime
from enum import Enum as PyEnum
from sqlalchemy import String, DateTime, Boolean, ForeignKey, Enum, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import Optional

from .base import Base


class DataType(PyEnum):
    FLOAT = "float"
    INT = "int"
    STRING = "string"


class DeviceParameter(Base):
    __tablename__ = "device_parameters"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    factory_id: Mapped[int] = mapped_column(ForeignKey("factories.id"), nullable=False)
    device_id: Mapped[int] = mapped_column(ForeignKey("devices.id"), nullable=False)
    parameter_key: Mapped[str] = mapped_column(String(100), nullable=False)
    display_name: Mapped[Optional[str]] = mapped_column(String(255))
    unit: Mapped[Optional[str]] = mapped_column(String(50))
    data_type: Mapped[DataType] = mapped_column(
        Enum(DataType, values_callable=lambda obj: [e.value for e in obj]),
        default=DataType.FLOAT
    )
    is_kpi_selected: Mapped[bool] = mapped_column(Boolean, default=True)
    discovered_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    device: Mapped["Device"] = relationship("Device", back_populates="parameters")

    __table_args__ = (
        Index("idx_factory_device", "factory_id", "device_id"),
        Index("idx_device_param", "device_id", "parameter_key"),
        {"mysql_charset": "utf8mb4", "mysql_collate": "utf8mb4_unicode_ci"},
    )
