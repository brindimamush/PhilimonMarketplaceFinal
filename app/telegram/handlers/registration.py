# File: app/telegram/handlers/registration.py
import logging
from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
    Update,
)
from telegram.ext import (
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)
from sqlalchemy import select

from app.config.logging import telegram_id_ctx
from app.database.session import AsyncSessionLocal
from app.database.models import User, BuyerProfile
from app.telegram.handlers.buyer_menu import send_buyer_main_menu
from app.translations import t

logger = logging.getLogger(__name__)

# State enumeration for conversation flow
CHOOSE_ROLE, BUYER_RULES, BUYER_CONTACT, BUYER_NAME = range(4)

# Platform Rules for Buyer Registration
BUYER_RULES_TEXT = (
    "📜 *Platform Rules: Buyer Edition*\n"
    "Welcome! Before registering as a buyer, please read and agree to the following rules.\n\n"
    "1️⃣ *Genuine Purchase Requests*\n"
    "Only submit a request if you genuinely intend to buy the product.\n\n"
    "2️⃣ *Accurate Product Information*\n"
    "Upload clear product images and provide exact details.\n\n"
    "3️⃣ *Respect Sellers' Time*\n"
    "Submit requests responsibly.\n\n"
    "4️⃣ *Select Offers Carefully*\n"
    "You can select one offer per request.\n\n"
    "5️⃣ *Payment Notice*\n"
    "Payments are settled directly with administrator guidance.\n\n"
    "6️⃣ *Fair Use*\n"
    "Spam or fake requests will result in suspension.\n\n"
    "Do you agree to the Buyer Platform Rules?"
)


async def start_registration(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Entry point for /start. Validates idempotency, active status, and menu routing."""
    user = update.effective_user
    if not user:
        return ConversationHandler.END

    telegram_id_ctx.set(user.id)

    async with AsyncSessionLocal() as session:
        stmt = select(User).where(User.telegram_id == user.id)
        db_user = (await session.execute(stmt)).scalar_one_or_none()

        if db_user and not db_user.is_active:
            msg_text = t("ACCOUNT_SUSPENDED", db_user.language or "en")
            if update.message:
                await update.message.reply_text(msg_text)
            elif update.callback_query and update.callback_query.message:
                await update.callback_query.message.edit_text(msg_text)
            return ConversationHandler.END

        if db_user and db_user.buyer_profile:
            await send_buyer_main_menu(update, context, db_user)
            return ConversationHandler.END

    keyboard = [
        [InlineKeyboardButton("🛒 Buyer", callback_data="role_buyer")],
        [InlineKeyboardButton("🏪 Seller", callback_data="role_seller")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    msg_text = "Welcome to the Marketplace! Please select your account type:"

    if update.message:
        await update.message.reply_text(msg_text, reply_markup=reply_markup)
    elif update.callback_query and update.callback_query.message:
        await update.callback_query.message.edit_text(msg_text, reply_markup=reply_markup)

    return CHOOSE_ROLE


async def choose_role(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    if not query:
        return CHOOSE_ROLE
    await query.answer()

    if query.data == "role_seller":
        await query.edit_message_text("Seller onboarding will open in future phases.")
        return ConversationHandler.END

    if query.data == "role_buyer":
        keyboard = [
            [
                InlineKeyboardButton("✅ I Agree", callback_data="rules_agree"),
                InlineKeyboardButton("❌ Cancel", callback_data="rules_cancel"),
            ]
        ]
        await query.edit_message_text(
            text=BUYER_RULES_TEXT,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown",
        )
        return BUYER_RULES

    return CHOOSE_ROLE


async def handle_rules(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    if not query:
        return BUYER_RULES
    await query.answer()

    if query.data == "rules_cancel":
        await query.edit_message_text("Registration cancelled.")
        return ConversationHandler.END

    if query.data == "rules_agree":
        keyboard = [[KeyboardButton("📱 Share Phone Number", request_contact=True)]]
        reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
        await query.message.delete()
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="Thank you! Please share your phone number using the button below:",
            reply_markup=reply_markup,
        )
        return BUYER_CONTACT

    return BUYER_RULES


async def receive_contact(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not update.message or not update.message.contact:
        return BUYER_CONTACT

    contact = update.message.contact
    if contact.user_id != update.effective_user.id:
        await update.message.reply_text("⚠️ Security Check Failed: Please share your own contact.")
        return BUYER_CONTACT

    context.user_data["phone_number"] = contact.phone_number
    await update.message.reply_text(
        "Phone number verified! ✅\n\nLastly, please enter your full name:",
        reply_markup=ReplyKeyboardRemove(),
    )
    return BUYER_NAME


async def receive_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Persists buyer profile and routes to main menu."""
    if not update.message or not update.message.text:
        return BUYER_NAME

    full_name = update.message.text.strip()
    phone_number = context.user_data.get("phone_number")
    telegram_id = update.effective_user.id
    language = update.effective_user.language_code or "en"
    if language not in ("en", "am"):
        language = "en"

    async with AsyncSessionLocal() as session:
        stmt = select(User).where(User.telegram_id == telegram_id)
        db_user = (await session.execute(stmt)).scalar_one_or_none()

        if not db_user:
            db_user = User(
                telegram_id=telegram_id,
                phone_number=phone_number,
                full_name=full_name,
                language=language,
                buyer_profile=BuyerProfile(),
            )
            session.add(db_user)
        else:
            db_user.phone_number = phone_number
            db_user.full_name = full_name
            if not db_user.buyer_profile:
                db_user.buyer_profile = BuyerProfile()

        await session.commit()

    context.user_data.clear()
    await send_buyer_main_menu(update, context, db_user)
    return ConversationHandler.END


def get_registration_handler() -> ConversationHandler:
    return ConversationHandler(
        entry_points=[CommandHandler("start", start_registration)],
        states={
            CHOOSE_ROLE: [CallbackQueryHandler(choose_role, pattern="^role_")],
            BUYER_RULES: [CallbackQueryHandler(handle_rules, pattern="^rules_")],
            BUYER_CONTACT: [MessageHandler(filters.CONTACT, receive_contact)],
            BUYER_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_name)],
        },
        fallbacks=[CommandHandler("start", start_registration)],
        name="buyer_registration_conversation",
        persistent=False,
    )