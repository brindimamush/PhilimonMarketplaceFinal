from enum import StrEnum


class SellerStatus(StrEnum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    DECLINED = "DECLINED"
    SUSPENDED = "SUSPENDED"


class RegistrationRequestStatus(StrEnum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    DECLINED = "DECLINED"


class ProductRequestStatus(StrEnum):
    DRAFT = "DRAFT"
    ACTIVE = "ACTIVE"
    CANCELLED = "CANCELLED"
    COMPLETED = "COMPLETED"
    EXPIRED = "EXPIRED"


class SellerResponseStatus(StrEnum):
    SUBMITTED = "SUBMITTED"
    ACCEPTED = "ACCEPTED"
    REJECTED = "REJECTED"


class NotificationType(StrEnum):
    BROADCAST = "BROADCAST"
    NEW_PRODUCT_REQUEST = "NEW_PRODUCT_REQUEST"
    NEW_SELLER_RESPONSE = "NEW_SELLER_RESPONSE"
    SELLER_APPROVED = "SELLER_APPROVED"
    SELLER_DECLINED = "SELLER_DECLINED"
    SYSTEM = "SYSTEM"


class NotificationStatus(StrEnum):
    PENDING = "PENDING"
    SENT = "SENT"
    FAILED = "FAILED"


class SupportRequestStatus(StrEnum):
    OPEN = "OPEN"
    IN_PROGRESS = "IN_PROGRESS"
    RESOLVED = "RESOLVED"
    CLOSED = "CLOSED"
