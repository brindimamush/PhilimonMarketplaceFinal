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

logger = logging.getLogger(__name__)

# State enumeration for conversation flow
CHOOSE_ROLE, BUYER_RULES, BUYER_CONTACT, BUYER_NAME = range(4)

# Platform Rules for Buyer Registration
BUYER_RULES_TEXT = (
    "📜 *Platform Rules: Buyer Edition*\n"
    "Welcome! Before registering as a buyer, please read and agree to the following rules.\n\n"
    "1️⃣ *Genuine Purchase Requests*\n"
    "Only submit a request if you genuinely intend to buy the product. Please do not submit fake, test, or non-serious requests.\n\n"
    "2️⃣ *Accurate Product Information*\n"
    "Upload a clear product-related image and provide the correct quantity or other requested information.\n\n"
    "3️⃣ *Respect Sellers' Time*\n"
    "Your request may be sent to multiple sellers. Please submit requests responsibly and avoid wasting sellers' time.\n\n"
    "4️⃣ *Select Offers Carefully*\n"
    "You may receive offers from different sellers. You can select only one offer for each request.\n"
    "Before confirming, you will be asked:\n\n"
    "Do you want to accept this price offer?\n"
    "Once you confirm, the selected seller will be notified.\n\n"
    "5️⃣ *Payment Notice*\n"
    "The platform currently does not process payments. Selecting an offer means you are interested in proceeding with that seller. Payment and final settlement will be handled separately with assistance from the platform administrator.\n\n"
    "6️⃣ *Fair Use*\n"
    "Spam, fake requests, abusive behavior, or repeated non-serious activity may result in your account being restricted or suspended.\n\n"
    "By selecting ✅ I Agree, you confirm that:\n"
    "You intend to make genuine purchase requests.\n"
    "The information and images you submit will be relevant and accurate.\n"
    "You understand that you can select only one seller offer per request.\n"
    "You understand that the platform does not currently process payments.\n"
    "You agree to use the platform responsibly.\n\n"
    "Do you agree to the Buyer Platform Rules?"
)


async def start_registration(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Entry point for /start. Validates idempotency, existing profiles, and active status."""
    user = update.effective_user
    if not user:
        return ConversationHandler.END

    telegram_id_ctx.set(user.id)

    async with AsyncSessionLocal() as session:
        stmt = select(User).where(User.telegram_id == user.id)
        db_user = (await session.execute(stmt)).scalar_one_or_none()

        # Handle suspended accounts
        if db_user and not db_user.is_active:
            msg_text = "❌ Your account is currently suspended. Please contact platform support."
            if update.message:
                await update.message.reply_text(msg_text)
            elif update.callback_query:
                await update.callback_query.message.edit_text(msg_text)
            return ConversationHandler.END

        # Registration idempotency check
        if db_user and db_user.buyer_profile:
            msg_text = (
                f"Welcome back, {db_user.full_name or user.first_name}! 👋\n\n"
                "You are registered as a Buyer.\n\n"
                "📍 *Main Menu*\n"
                "• Send /start to display this menu at any time."
            )
            if update.message:
                await update.message.reply_text(msg_text, parse_mode="Markdown")
            elif update.callback_query:
                await update.callback_query.message.edit_text(msg_text, parse_mode="Markdown")
            return ConversationHandler.END

    # Role selection prompt
    keyboard = [
        [InlineKeyboardButton("🛒 Buyer", callback_data="role_buyer")],
        [InlineKeyboardButton("🏪 Seller", callback_data="role_seller")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    msg_text = "Welcome to the Marketplace! Please select your account type:"

    if update.message:
        await update.message.reply_text(msg_text, reply_markup=reply_markup)
    elif update.callback_query:
        await update.callback_query.message.edit_text(msg_text, reply_markup=reply_markup)

    return CHOOSE_ROLE


async def choose_role(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Processes user role choice."""
    query = update.callback_query
    if not query:
        return CHOOSE_ROLE
    await query.answer()

    if query.data == "role_seller":
        await query.edit_message_text(
            "Seller onboarding will open in Phase 4. Stay tuned!"
        )
        return ConversationHandler.END

    if query.data == "role_buyer":
        keyboard = [
            [
                InlineKeyboardButton("✅ I Agree", callback_data="rules_agree"),
                InlineKeyboardButton("❌ Cancel", callback_data="rules_cancel"),
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            text=BUYER_RULES_TEXT,
            reply_markup=reply_markup,
            parse_mode="Markdown",
        )
        return BUYER_RULES

    return CHOOSE_ROLE


async def handle_rules(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handles platform rules acceptance or cancellation."""
    query = update.callback_query
    if not query:
        return BUYER_RULES
    await query.answer()

    if query.data == "rules_cancel":
        await query.edit_message_text(
            "Registration cancelled. You must accept the buyer rules to access marketplace features."
        )
        return ConversationHandler.END

    if query.data == "rules_agree":
        keyboard = [
            [KeyboardButton("📱 Share Phone Number", request_contact=True)]
        ]
        reply_markup = ReplyKeyboardMarkup(
            keyboard, one_time_keyboard=True, resize_keyboard=True
        )
        await query.message.delete()
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="Thank you! Please share your phone number using the button below:",
            reply_markup=reply_markup,
        )
        return BUYER_CONTACT

    return BUYER_RULES


async def receive_contact(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Verifies contact ownership against current Telegram ID."""
    if not update.message or not update.message.contact:
        await update.message.reply_text(
            "Please tap the '📱 Share Phone Number' button below to continue."
        )
        return BUYER_CONTACT

    contact = update.message.contact
    user_id = update.effective_user.id

    # Telegram Security Rule validation
    if contact.user_id != user_id:
        logger.warning(
            "Contact mismatch detected",
            extra={
                "operation": "buyer_registration",
                "status": "failed",
                "telegram_id": user_id,
            },
        )
        await update.message.reply_text(
            "⚠️ Security Check Failed: You must share your own Telegram contact number. "
            "Please use the button below."
        )
        return BUYER_CONTACT

    context.user_data["phone_number"] = contact.phone_number

    await update.message.reply_text(
        "Phone number verified! ✅\n\nLastly, please enter your full name:",
        reply_markup=ReplyKeyboardRemove(),
    )
    return BUYER_NAME


async def receive_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Persists User and BuyerProfile entities atomically."""
    if not update.message or not update.message.text:
        await update.message.reply_text("Please enter a valid text name.")
        return BUYER_NAME

    full_name = update.message.text.strip()
    phone_number = context.user_data.get("phone_number")
    telegram_id = update.effective_user.id
    language = update.effective_user.language_code or "en"

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

        logger.info(
            "Buyer registration complete",
            extra={
                "operation": "buyer_registration",
                "entity_id": str(db_user.id),
                "status": "success",
            },
        )

    context.user_data.clear()

    await update.message.reply_text(
        f"🎉 Welcome aboard, {full_name}!\n\n"
        "Your Buyer account is ready.\n\n"
        "📍 *Main Menu*\n"
        "• Send /start to open your menu anytime.",
        parse_mode="Markdown",
    )
    return ConversationHandler.END


def get_registration_handler() -> ConversationHandler:
    """Constructs the Phase 3 Buyer Registration conversation pipeline."""
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