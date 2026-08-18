import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.database.models import BuyerProfile, SellerProfile, User
from app.domain.enums import SellerStatus


@pytest.mark.asyncio
async def test_create_user_with_profiles(db_session: AsyncSession):
    """Verify primary user entity and 1:1 Buyer/Seller profile associations."""
    telegram_id = 999888777

    # Create primary user
    user = User(telegram_id=telegram_id, full_name="John Doe", language="en")
    db_session.add(user)
    await db_session.flush()

    # Create associated profiles
    buyer_profile = BuyerProfile(user_id=user.id)
    seller_profile = SellerProfile(
        user_id=user.id,
        business_name="John Tech",
        location="Downtown",
        product_category="Electronics",
        status=SellerStatus.PENDING,
    )
    db_session.add_all([buyer_profile, seller_profile])
    await db_session.commit()
    # Query back using selectinload for async relationship access
    stmt = (
        select(User)
        .where(User.telegram_id == telegram_id)
        .options(selectinload(User.buyer_profile), selectinload(User.seller_profile))
    )
    # Query back
    result = await db_session.execute(stmt)
    fetched_user = result.scalar_one()

    assert fetched_user.full_name == "John Doe"
    assert fetched_user.buyer_profile is not None
    assert fetched_user.seller_profile is not None
    assert fetched_user.seller_profile.status == SellerStatus.PENDING
