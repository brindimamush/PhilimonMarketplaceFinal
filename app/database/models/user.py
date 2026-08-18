import uuid
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, Boolean, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base

if TYPE_CHECKING:
    from app.database.models.profiles import (
        BuyerProfile,
        SellerProfile,
        SellerRegistrationRequest,
    )


class User(Base):
    """Core user entity representing a Telegram account."""

    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True, nullable=False)
    phone_number: Mapped[str | None] = mapped_column(String(32), nullable=True)
    full_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    language: Mapped[str] = mapped_column(String(10), default="en", nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Relationships
    buyer_profile: Mapped["BuyerProfile | None"] = relationship(
        "BuyerProfile", back_populates="user", uselist=False, cascade="all, delete-orphan"
    )
    seller_profile: Mapped["SellerProfile | None"] = relationship(
        "SellerProfile",
        foreign_keys="[SellerProfile.user_id]",
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    registration_requests: Mapped[list["SellerRegistrationRequest"]] = relationship(
        "SellerRegistrationRequest",
        foreign_keys="[SellerRegistrationRequest.user_id]",
        back_populates="user",
        cascade="all, delete-orphan",
    )
