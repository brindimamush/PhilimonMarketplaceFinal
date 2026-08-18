# File: tests/test_buyer_menu.py
"""Tests for Phase 4 buyer menu, localization layer, and language switching."""

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import BuyerProfile, User
from app.telegram.handlers.buyer_menu import (
    get_buyer_main_keyboard,
    
)
from app.translations import t


@pytest.mark.asyncio
async def test_translations_utility():
    """Verify localization lookup and default fallbacks."""
    assert t("BTN_NEW_REQUEST", "en") == "🛒 New Request"
    assert t("BTN_NEW_REQUEST", "am") == "🛒 አዲስ ትዕዛዝ"
    # Fallback to English for unsupported locale
    assert t("BTN_NEW_REQUEST", "fr") == "🛒 New Request"


@pytest.mark.asyncio
async def test_keyboard_generation():
    """Verify reply keyboard localized button labels."""
    keyboard_en = get_buyer_main_keyboard("en")
    assert keyboard_en.keyboard[0][0].text == "🛒 New Request"
    assert keyboard_en.keyboard[0][1].text == "🌐 Language"

    keyboard_am = get_buyer_main_keyboard("am")
    assert keyboard_am.keyboard[0][0].text == "🛒 አዲስ ትዕዛዝ"
    assert keyboard_am.keyboard[0][1].text == "🌐 ቋንቋ"


@pytest.mark.asyncio
async def test_language_switch_persistence_and_messaging(db_session: AsyncSession):
    """Verify that changing language updates users.language in DB and alters subsequent responses."""
    telegram_id = 123456789

    user = User(
        telegram_id=telegram_id,
        full_name="Abebe Bikila",
        language="en",
        buyer_profile=BuyerProfile(),
    )
    db_session.add(user)
    await db_session.commit()

    # Query initial state
    stmt = select(User).where(User.telegram_id == telegram_id)
    db_user = (await db_session.execute(stmt)).scalar_one()
    assert db_user.language == "en"
    assert t("NEW_REQUEST_RESPONSE", db_user.language) == "🛒 Sourcing request workflow will open in Phase 5."

    # Simulate language update to Amharic
    db_user.language = "am"
    await db_session.commit()

    # Verify persistent DB state update
    updated_user = (await db_session.execute(stmt)).scalar_one()
    assert updated_user.language == "am"
    assert t("NEW_REQUEST_RESPONSE", updated_user.language) == "🛒 አዲስ ትዕዛዝ የማስገባት አገልግሎት በክፍል 5 ይለቀቃል።"