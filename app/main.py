import asyncio
import logging

from telegram.ext import ApplicationBuilder, CommandHandler

from app.config.logging import setup_logging
from app.config.settings import settings
from app.database.session import check_db_health
from app.telegram.handlers.common import start_handler
from app.utils.redis import check_redis_health, redis_client

setup_logging(settings.LOG_LEVEL)
logger = logging.getLogger(__name__)


async def main() -> None:
    """Application bootstrapper fulfilling Phase 1 system checks."""
    logger.info("Starting Modular Monolith Marketplace Core...")

    # Validate Infrastructure Services
    if not await check_db_health():
        raise RuntimeError("Fatal: PostgreSQL connection failed.")
    logger.info("PostgreSQL Service: Connected OK.")

    if not await check_redis_health():
        raise RuntimeError("Fatal: Redis connection failed.")
    logger.info("Redis Service: Connected OK.")

    # Initialize Telegram Application
    application = ApplicationBuilder().token(settings.BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", start_handler))

    await application.initialize()
    await application.start()
    if application.updater:
        await application.updater.start_polling()

    logger.info("Telegram Bot Polling Operational. Marketplace Ready.")

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
