# app/core/models/user.py
from __future__ import annotations
from typing import Optional
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy import String, Boolean, DateTime, func, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB

class Base(DeclarativeBase):
    pass


class AppUser(Base):
    """
    Пользователь приложения. Связан с Keycloak по sub.
    """
    __tablename__ = "app_user"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)

    username: Mapped[str] = mapped_column(String(255), index=True)
    email: Mapped[Optional[str]] = mapped_column(String(255), index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    created_at: Mapped[Optional["DateTime"]] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[Optional["DateTime"]] = mapped_column(DateTime(timezone=True), onupdate=func.now())

    settings: Mapped["AppUserSettings"] = relationship(
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan",
        lazy="joined",
    )


class AppUserSettings(Base):
    """
    Локальные настройки пользователей
    """
    __tablename__ = "app_user_settings"
    __table_args__ = (
        UniqueConstraint("user_id", name="uq_app_user_settings_user_id"),
    )

    user_id: Mapped[str] = mapped_column(ForeignKey("app_user.id", ondelete="CASCADE"), primary_key=True)
    locale: Mapped[str] = mapped_column(String(16), default="ru-RU", nullable=False)
    theme: Mapped[str] = mapped_column(String(16), default="system", nullable=False)
    notifications: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)

    user: Mapped[AppUser] = relationship(back_populates="settings")