from datetime import datetime
from enum import Enum as PyEnum
from sqlalchemy import String, DateTime, Boolean, ForeignKey, JSON, Enum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import Optional, Dict, Any

from .base import Base


class UserRole(PyEnum):
    SUPER_ADMIN = "super_admin"
    ADMIN = "admin"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    factory_id: Mapped[int] = mapped_column(ForeignKey("factories.id"), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    whatsapp_number: Mapped[Optional[str]] = mapped_column(String(50))
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole, values_callable=lambda obj: [e.value for e in obj]),
        nullable=False,
        default=UserRole.ADMIN
    )
    permissions: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    invite_token: Mapped[Optional[str]] = mapped_column(String(255))
    invited_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    last_login: Mapped[Optional[datetime]] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    factory: Mapped["Factory"] = relationship("Factory", back_populates="users")

    __table_args__ = (
        {"mysql_charset": "utf8mb4", "mysql_collate": "utf8mb4_unicode_ci"},
    )
