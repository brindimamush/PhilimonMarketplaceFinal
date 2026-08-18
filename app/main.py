# File: app/main.py
import asyncio
import logging

from telegram.ext import ApplicationBuilder

from app.config.logging import setup_logging
from app.config.settings import settings
from app.database.session import check_db_health
from app.telegram.handlers.buyer_menu import get_buyer_menu_handlers
from app.telegram.handlers.registration import get_registration_handler
from app.utils.redis import check_redis_health, redis_client

setup_logging(settings.LOG_LEVEL)
logger = logging.getLogger(__name__)


async def main() -> None:
    """Application bootstrapper."""
    logger.info("Starting Modular Monolith Marketplace Core...")

    if not await check_db_health():
        raise RuntimeError("Fatal: PostgreSQL connection failed.")
    if not await check_redis_health():
        raise RuntimeError("Fatal: Redis connection failed.")

    application = ApplicationBuilder().token(settings.BOT_TOKEN).build()

    # Register registration flow and buyer menu handlers
    application.add_handler(get_registration_handler())
    for handler in get_buyer_menu_handlers():
        application.add_handler(handler)

    await application.initialize()
    await application.start()
    if application.updater:
        await application.updater.start_polling()

    logger.info("Telegram Bot Polling Operational. Marketplace Phase 4 Ready.")

    stop_event = asyncio.Event()
    try:
        await stop_event.wait()
    except (KeyboardInterrupt, SystemExit):
        logger.info("Shutting down...")
    finally:
        if application.updater:
            await application.updater.stop()
        await application.stop()
        await application.shutdown()
        await redis_client.aclose()


if __name__ == "__main__":
    asyncio.run(main())