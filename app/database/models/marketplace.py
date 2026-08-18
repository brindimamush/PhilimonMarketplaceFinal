import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Numeric, String, Text
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.domain.enums import ProductRequestStatus, SellerResponseStatus

if TYPE_CHECKING:
    from app.database.models.user import User


class ProductRequest(Base):
    """Buyer initiated sourcing request."""

    __tablename__ = "product_requests"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    buyer_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    category: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    budget_min: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)
    budget_max: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)
    status: Mapped[ProductRequestStatus] = mapped_column(
        SQLEnum(ProductRequestStatus, name="product_request_status_enum"),
        default=ProductRequestStatus.ACTIVE,
        nullable=False,
        index=True,
    )
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    buyer: Mapped["User"] = relationship("User")
    images: Mapped[list["RequestImage"]] = relationship(
        "RequestImage", back_populates="product_request", cascade="all, delete-orphan"
    )
    responses: Mapped[list["SellerResponse"]] = relationship(
        "SellerResponse", back_populates="product_request", cascade="all, delete-orphan"
    )
    selection: Mapped["BuyerSelection | None"] = relationship(
        "BuyerSelection",
        back_populates="product_request",
        uselist=False,
        cascade="all, delete-orphan",
    )


class RequestImage(Base):
    """Images attached to product requests, referenced by Telegram file_ids."""

    __tablename__ = "request_images"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    product_request_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("product_requests.id", ondelete="CASCADE"), nullable=False, index=True
    )
    telegram_file_id: Mapped[str] = mapped_column(String(255), nullable=False)
    file_unique_id: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Relationships
    product_request: Mapped["ProductRequest"] = relationship(
        "ProductRequest", back_populates="images"
    )


class SellerResponse(Base):
    """Offers submitted by sellers in response to a Product Request."""

    __tablename__ = "seller_responses"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    product_request_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("product_requests.id", ondelete="CASCADE"), nullable=False, index=True
    )
    seller_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    price: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[SellerResponseStatus] = mapped_column(
        SQLEnum(SellerResponseStatus, name="seller_response_status_enum"),
        default=SellerResponseStatus.SUBMITTED,
        nullable=False,
    )

    # Relationships
    product_request: Mapped["ProductRequest"] = relationship(
        "ProductRequest", back_populates="responses"
    )
    seller: Mapped["User"] = relationship("User")


class BuyerSelection(Base):
    """Winning offer selection made by a buyer."""

    __tablename__ = "buyer_selections"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    product_request_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("product_requests.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True,
    )
    seller_response_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("seller_responses.id", ondelete="CASCADE"), nullable=False, index=True
    )
    selected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    # Relationships
    product_request: Mapped["ProductRequest"] = relationship(
        "ProductRequest", back_populates="selection"
    )
    seller_response: Mapped["SellerResponse"] = relationship("SellerResponse")
