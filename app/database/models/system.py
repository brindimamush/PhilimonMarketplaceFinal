import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy import (
    Enum as SQLEnum,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.domain.enums import NotificationStatus, NotificationType, SupportRequestStatus

if TYPE_CHECKING:
    from app.database.models.user import User


class Notification(Base):
    """Queue and record of system and transactional notifications."""

    __tablename__ = "notifications"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    type: Mapped[NotificationType] = mapped_column(
        SQLEnum(NotificationType, name="notification_type_enum"), nullable=False
    )
    payload: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    status: Mapped[NotificationStatus] = mapped_column(
        SQLEnum(NotificationStatus, name="notification_status_enum"),
        default=NotificationStatus.PENDING,
        nullable=False,
        index=True,
    )
    retry_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    user: Mapped["User"] = relationship("User")


class SupportRequest(Base):
    """User support requests and ticket tracking."""

    __tablename__ = "support_requests"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    subject: Mapped[str] = mapped_column(String(255), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[SupportRequestStatus] = mapped_column(
        SQLEnum(SupportRequestStatus, name="support_request_status_enum"),
        default=SupportRequestStatus.OPEN,
        nullable=False,
        index=True,
    )
    resolved_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    user: Mapped["User"] = relationship("User", foreign_keys=[user_id])
    resolver: Mapped["User | None"] = relationship("User", foreign_keys=[resolved_by])


class Suspension(Base):
    """Account and entity suspension records."""

    __tablename__ = "suspensions"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    suspended_by: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)

    # Relationships
    user: Mapped["User"] = relationship("User", foreign_keys=[user_id])
    suspender: Mapped["User"] = relationship("User", foreign_keys=[suspended_by])


class IdempotencyKey(Base):
    """Deduplication keys for transactional operations."""

    __tablename__ = "idempotency_keys"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    key: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    request_path: Mapped[str] = mapped_column(String(255), nullable=False)
    response_payload: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)


class AuditLog(Base):
    """Append-only audit trail for administrative and operational changes."""

    __tablename__ = "audit_logs"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    action: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    entity_type: Mapped[str] = mapped_column(String(100), nullable=False)
    entity_id: Mapped[uuid.UUID | None] = mapped_column(nullable=True)
    changes: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)

    # Relationships
    user: Mapped["User | None"] = relationship("User")


class BotState(Base):
    """PostgreSQL fallback state store for Telegram Conversations/FSM."""

    __tablename__ = "bot_states"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True, nullable=False)
    state_name: Mapped[str] = mapped_column(String(100), nullable=False)
    context_data: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
