# File: app/telegram/handlers/seller_registration.py
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
from app.database.models import User, SellerRegistrationRequest
from app.domain.enums import RegistrationRequestStatus
from app.translations import get_all_button_texts

logger = logging.getLogger(__name__)

# State enumerations for the Seller Conversation
(
    SELLER_RULES,
    SELLER_CONTACT,
    SELLER_NAME,
    SELLER_BUSINESS_NAME,
    SELLER_LOCATION,
    SELLER_CATEGORY,
    SELLER_SHOP_NUMBER,
    SELLER_CONFIRMATION,
) = range(20, 28)

# Platform Rules: Seller Edition as specified in the requirements
SELLER_RULES_TEXT = (
    "📜 *Platform Rules: Seller Edition*\n"
    "By continuing, you confirm that:\n\n"
    "A. *Genuine Fulfillment*\n"
    "You will accept buyer requests only when you genuinely believe that you can fulfill them.\n\n"
    "B. *Accurate Pricing*\n"
    "You will provide accurate prices and will not submit fake or misleading offers.\n\n"
    "C. *Accurate Business Information*\n"
    "You confirm that the personal and business information you provide is accurate.\n\n"
    "D. *Fair Marketplace Participation*\n"
    "You will not manipulate requests, buyers, sellers, or the platform.\n\n"
    "E. *No Guarantee of Selection*\n"
    "You understand that submitting an offer does not guarantee that the buyer will select it.\n\n"
    "F. *Account Restrictions*\n"
    "Repeated failure to respond responsibly, fulfill accepted commitments, or comply with platform rules may result in suspension or account restrictions.\n\n"
    "By selecting “I Agree”, you confirm that you have read and accepted the Seller Platform Usage Agreement."
)


async def start_seller_registration(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Entry point: Triggered via 'Switch to Seller' button or 'role_seller' inline query."""
    user = update.effective_user
    if user:
        telegram_id_ctx.set(user.id)

    keyboard = [
        [
            InlineKeyboardButton("✅ I Agree", callback_data="seller_rules_agree"),
            InlineKeyboardButton("❌ Cancel", callback_data="seller_rules_cancel"),
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text(
            text=SELLER_RULES_TEXT, reply_markup=reply_markup, parse_mode="Markdown"
        )
    elif update.message:
        await update.message.reply_text(
            text=SELLER_RULES_TEXT, reply_markup=reply_markup, parse_mode="Markdown"
        )

    return SELLER_RULES


async def handle_seller_rules(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handles rules agreement and branches to Case A (New) or Case B (Existing)."""
    query = update.callback_query
    if not query:
        return SELLER_RULES
    await query.answer()

    if query.data == "seller_rules_cancel":
        await query.edit_message_text("Seller registration cancelled.")
        return ConversationHandler.END

    if query.data == "seller_rules_agree":
        user_id = update.effective_user.id
        
        async with AsyncSessionLocal() as session:
            stmt = select(User).where(User.telegram_id == user_id)
            db_user = (await session.execute(stmt)).scalar_one_or_none()

        # Case B: Existing buyer profile with phone and name already recorded
        if db_user and db_user.phone_number and db_user.full_name:
            context.user_data['existing_user'] = True
            await query.message.delete()
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="Welcome back! Let's register your shop.\n\nPlease enter your *Business Name*:",
                parse_mode="Markdown"
            )
            return SELLER_BUSINESS_NAME

        # Case A: New user or missing basic profile details
        context.user_data['existing_user'] = False
        keyboard = [[KeyboardButton("📱 Share Phone Number", request_contact=True)]]
        reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
        await query.message.delete()
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="Please share your phone number using the button below:",
            reply_markup=reply_markup,
        )
        return SELLER_CONTACT


async def receive_seller_contact(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Case A: Receives phone number."""
    if not update.message or not update.message.contact:
        return SELLER_CONTACT

    contact = update.message.contact
    if contact.user_id != update.effective_user.id:
        await update.message.reply_text("⚠️ Please share your own contact.")
        return SELLER_CONTACT

    context.user_data["phone_number"] = contact.phone_number
    await update.message.reply_text(
        "Phone number verified! ✅\n\nPlease enter your *Full Name*:",
        reply_markup=ReplyKeyboardRemove(),
        parse_mode="Markdown"
    )
    return SELLER_NAME


async def receive_seller_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Case A: Receives full name."""
    if not update.message or not update.message.text:
        return SELLER_NAME

    context.user_data["full_name"] = update.message.text.strip()
    await update.message.reply_text("Thank you! Now, please enter your *Business Name*:", parse_mode="Markdown")
    return SELLER_BUSINESS_NAME


async def receive_seller_business_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Receives business name (Common to Case A and B)."""
    if not update.message or not update.message.text:
        return SELLER_BUSINESS_NAME

    context.user_data["business_name"] = update.message.text.strip()
    await update.message.reply_text("Where is your business located? (e.g., Piassa, Bole):")
    return SELLER_LOCATION


async def receive_seller_location(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Receives physical location."""
    if not update.message or not update.message.text:
        return SELLER_LOCATION

    context.user_data["location"] = update.message.text.strip()
    await update.message.reply_text("What is your primary *Product Category*? (e.g., Electronics, Fashion):", parse_mode="Markdown")
    return SELLER_CATEGORY


async def receive_seller_category(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Receives product category."""
    if not update.message or not update.message.text:
        return SELLER_CATEGORY

    context.user_data["product_category"] = update.message.text.strip()
    await update.message.reply_text("Finally, what is your *Shop Number*? (Enter 'N/A' if not applicable):", parse_mode="Markdown")
    return SELLER_SHOP_NUMBER


async def receive_seller_shop_number(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Receives shop number and builds confirmation summary."""
    if not update.message or not update.message.text:
        return SELLER_SHOP_NUMBER

    context.user_data["shop_number"] = update.message.text.strip()

    # Determine display name and phone based on Case A or Case B
    async with AsyncSessionLocal() as session:
        stmt = select(User).where(User.telegram_id == update.effective_user.id)
        db_user = (await session.execute(stmt)).scalar_one_or_none()

    if context.user_data.get("existing_user") and db_user:
        name = db_user.full_name
        phone = db_user.phone_number
    else:
        name = context.user_data.get("full_name")
        phone = context.user_data.get("phone_number")

    summary = (
        "📋 *Please confirm your details:*\n\n"
        f"👤 *Name:* {name}\n"
        f"📱 *Phone:* {phone}\n"
        f"🏢 *Business:* {context.user_data.get('business_name')}\n"
        f"📍 *Location:* {context.user_data.get('location')}\n"
        f"🏷 *Category:* {context.user_data.get('product_category')}\n"
        f"🏪 *Shop Number:* {context.user_data.get('shop_number')}"
    )

    keyboard = [
        [InlineKeyboardButton("✅ Confirm", callback_data="seller_confirm")],
        [
            InlineKeyboardButton("✏️ Edit", callback_data="seller_edit"),
            InlineKeyboardButton("❌ Cancel", callback_data="seller_cancel")
        ]
    ]

    await update.message.reply_text(
        summary,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )
    return SELLER_CONFIRMATION


async def handle_seller_confirmation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Processes final confirmation, creates PENDING request."""
    query = update.callback_query
    if not query:
        return SELLER_CONFIRMATION
    await query.answer()

    if query.data == "seller_cancel":
        await query.edit_message_text("Seller registration cancelled.")
        context.user_data.clear()
        return ConversationHandler.END

    if query.data == "seller_edit":
        await query.edit_message_text(
            "Let's update your business details.\n\nPlease enter your *Business Name*:", 
            parse_mode="Markdown"
        )
        return SELLER_BUSINESS_NAME

    if query.data == "seller_confirm":
        telegram_id = update.effective_user.id

        async with AsyncSessionLocal() as session:
            stmt = select(User).where(User.telegram_id == telegram_id)
            db_user = (await session.execute(stmt)).scalar_one_or_none()

            # Persist Case A profile updates
            if not db_user:
                db_user = User(
                    telegram_id=telegram_id,
                    phone_number=context.user_data.get("phone_number"),
                    full_name=context.user_data.get("full_name"),
                    language=update.effective_user.language_code or "en"
                )
                session.add(db_user)
                await session.flush()
            elif not context.user_data.get("existing_user"):
                db_user.phone_number = context.user_data.get("phone_number")
                db_user.full_name = context.user_data.get("full_name")

            # Create PENDING SellerRegistrationRequest
            registration_req = SellerRegistrationRequest(
                user_id=db_user.id,
                business_name=context.user_data.get("business_name"),
                location=context.user_data.get("location"),
                product_category=context.user_data.get("product_category"),
                shop_number=context.user_data.get("shop_number"),
                status=RegistrationRequestStatus.PENDING
            )
            session.add(registration_req)
            await session.commit()

        await query.edit_message_text(
            "✅ *Registration Submitted!*\n\n"
            "Your seller profile request is currently `PENDING`. "
            "Our team will review your application shortly.",
            parse_mode="Markdown"
        )
        context.user_data.clear()
        return ConversationHandler.END

    return SELLER_CONFIRMATION


def get_seller_registration_handler() -> ConversationHandler:
    """Builds and exposes the self-contained seller registration state machine."""
    return ConversationHandler(
        entry_points=[
            CallbackQueryHandler(start_seller_registration, pattern="^role_seller$"),
            MessageHandler(filters.TEXT & filters.Text(get_all_button_texts("BTN_SWITCH_SELLER")), start_seller_registration)
        ],
        states={
            SELLER_RULES: [CallbackQueryHandler(handle_seller_rules, pattern="^seller_rules_")],
            SELLER_CONTACT: [MessageHandler(filters.CONTACT, receive_seller_contact)],
            SELLER_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_seller_name)],
            SELLER_BUSINESS_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_seller_business_name)],
            SELLER_LOCATION: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_seller_location)],
            SELLER_CATEGORY: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_seller_category)],
            SELLER_SHOP_NUMBER: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_seller_shop_number)],
            SELLER_CONFIRMATION: [CallbackQueryHandler(handle_seller_confirmation, pattern="^seller_")],
        },
        fallbacks=[CommandHandler("start", start_seller_registration)],
        name="seller_registration_conversation",
        persistent=False,
    )