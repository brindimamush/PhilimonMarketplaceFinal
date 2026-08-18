import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.domain.enums import RegistrationRequestStatus, SellerStatus

if TYPE_CHECKING:
    from app.database.models.user import User


class BuyerProfile(Base):
    """Buyer profile bound 1:1 to a primary User account."""

    __tablename__ = "buyer_profiles"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False, index=True
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="buyer_profile")


class SellerProfile(Base):
    """Seller profile containing verified business credentials."""

    __tablename__ = "seller_profiles"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False, index=True
    )
    business_name: Mapped[str] = mapped_column(String(255), nullable=False)
    location: Mapped[str] = mapped_column(String(255), nullable=False)
    product_category: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    shop_number: Mapped[str | None] = mapped_column(String(50), nullable=True)
    status: Mapped[SellerStatus] = mapped_column(
        SQLEnum(SellerStatus, name="seller_status_enum"),
        default=SellerStatus.PENDING,
        nullable=False,
        index=True,
    )
    approved_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    user: Mapped["User"] = relationship(
        "User", foreign_keys=[user_id], back_populates="seller_profile"
    )
    approver: Mapped["User | None"] = relationship("User", foreign_keys=[approved_by])


class SellerRegistrationRequest(Base):
    """Audit log and pipeline for onboarding new marketplace sellers."""

    __tablename__ = "seller_registration_requests"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    business_name: Mapped[str] = mapped_column(String(255), nullable=False)
    location: Mapped[str] = mapped_column(String(255), nullable=False)
    product_category: Mapped[str] = mapped_column(String(100), nullable=False)
    shop_number: Mapped[str | None] = mapped_column(String(50), nullable=True)
    status: Mapped[RegistrationRequestStatus] = mapped_column(
        SQLEnum(RegistrationRequestStatus, name="registration_request_status_enum"),
        default=RegistrationRequestStatus.PENDING,
        nullable=False,
        index=True,
    )
    reviewed_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    user: Mapped["User"] = relationship(
        "User", foreign_keys=[user_id], back_populates="registration_requests"
    )
    reviewer: Mapped["User | None"] = relationship("User", foreign_keys=[reviewed_by])
