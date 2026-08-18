# File: app/telegram/handlers/buyer_menu.py
"""Telegram handlers for the Buyer Main Menu and Language Switcher."""

import logging
from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ReplyKeyboardMarkup,
    Update,
)
from telegram.ext import (
    CallbackQueryHandler,
    ContextTypes,
    MessageHandler,
    filters,
)
from sqlalchemy import select

from app.config.logging import telegram_id_ctx
from app.database.models import User
from app.database.session import AsyncSessionLocal
from app.translations import get_all_button_texts, t

logger = logging.getLogger(__name__)


def get_buyer_main_keyboard(lang: str = "en") -> ReplyKeyboardMarkup:
    """Generates localized persistent reply keyboard layout for buyers."""
    keyboard = [
        [t("BTN_NEW_REQUEST", lang), t("BTN_LANGUAGE", lang)],
        [t("BTN_SWITCH_SELLER", lang), t("BTN_SUPPORT", lang)],
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


def get_language_inline_keyboard() -> InlineKeyboardMarkup:
    """Generates inline language selection keyboard."""
    keyboard = [
        [
            InlineKeyboardButton("🇬🇧 English", callback_data="set_lang_en"),
            InlineKeyboardButton("🇪🇹 አማርኛ", callback_data="set_lang_am"),
        ]
    ]
    return InlineKeyboardMarkup(keyboard)


async def send_buyer_main_menu(
    update: Update, context: ContextTypes.DEFAULT_TYPE, user: User
) -> None:
    """Helper to render localized buyer main menu."""
    lang = user.language or "en"
    display_name = user.full_name or (
        update.effective_user.first_name if update.effective_user else "User"
    )
    text = t("MAIN_MENU_TITLE", lang, name=display_name)
    reply_markup = get_buyer_main_keyboard(lang)

    if update.message:
        await update.message.reply_text(text, reply_markup=reply_markup, parse_mode="Markdown")
    elif update.callback_query and update.callback_query.message:
        await update.callback_query.message.reply_text(
            text, reply_markup=reply_markup, parse_mode="Markdown"
        )


async def get_current_user(telegram_id: int) -> User | None:
    """Fetch user entity by telegram ID."""
    async with AsyncSessionLocal() as session:
        stmt = select(User).where(User.telegram_id == telegram_id)
        return (await session.execute(stmt)).scalar_one_or_none()


async def handle_new_request(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handler for 🛒 New Request button."""
    if not update.effective_user or not update.message:
        return
    telegram_id_ctx.set(update.effective_user.id)
    user = await get_current_user(update.effective_user.id)
    lang = user.language if user else "en"
    await update.message.reply_text(t("NEW_REQUEST_RESPONSE", lang))


async def handle_language_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handler for 🌐 Language button."""
    if not update.effective_user or not update.message:
        return
    telegram_id_ctx.set(update.effective_user.id)
    user = await get_current_user(update.effective_user.id)
    lang = user.language if user else "en"
    await update.message.reply_text(
        t("SELECT_LANGUAGE", lang),
        reply_markup=get_language_inline_keyboard(),
    )


async def handle_support(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handler for 🆘 Support button."""
    if not update.effective_user or not update.message:
        return
    telegram_id_ctx.set(update.effective_user.id)
    user = await get_current_user(update.effective_user.id)
    lang = user.language if user else "en"
    await update.message.reply_text(t("SUPPORT_RESPONSE", lang))


async def handle_language_callback(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Processes language switch inline callbacks and updates users.language in DB."""
    query = update.callback_query
    if not query or not update.effective_user:
        return
    await query.answer()

    telegram_id_ctx.set(update.effective_user.id)
    target_lang = query.data.replace("set_lang_", "")

    async with AsyncSessionLocal() as session:
        stmt = select(User).where(User.telegram_id == update.effective_user.id)
        db_user = (await session.execute(stmt)).scalar_one_or_none()

        if db_user:
            db_user.language = target_lang
            await session.commit()
            logger.info(
                "User language updated",
                extra={
                    "operation": "update_language",
                    "entity_id": str(db_user.id),
                    "status": "success",
                },
            )

            # Send localized feedback and re-render main menu keyboard
            await query.edit_message_text(t("LANGUAGE_CHANGED", target_lang))
            await send_buyer_main_menu(update, context, db_user)


def get_buyer_menu_handlers() -> list:
    """Returns buyer main menu message handlers matching all language button variants."""
    return [
        MessageHandler(
            filters.TEXT & filters.Text(get_all_button_texts("BTN_NEW_REQUEST")),
            handle_new_request,
        ),
        MessageHandler(
            filters.TEXT & filters.Text(get_all_button_texts("BTN_LANGUAGE")),
            handle_language_menu,
        ),
       
        MessageHandler(
            filters.TEXT & filters.Text(get_all_button_texts("BTN_SUPPORT")),
            handle_support,
        ),
        CallbackQueryHandler(handle_language_callback, pattern="^set_lang_"),
    ]