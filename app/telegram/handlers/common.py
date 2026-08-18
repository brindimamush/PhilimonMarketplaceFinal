import logging

from telegram import Update
from telegram.ext import ContextTypes

from app.config.logging import telegram_id_ctx

logger = logging.getLogger(__name__)


async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Entry point handler verifying pipeline health."""
    user = update.effective_user
    if user:
        telegram_id_ctx.set(user.id)

    logger.info(
        "Received /start command",
        extra={"operation": "start_command", "status": "success"},
    )
    if update.message:
        await update.message.reply_text("Marketplace Service Operational.")
