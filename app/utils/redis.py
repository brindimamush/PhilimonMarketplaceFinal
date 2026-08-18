import logging

from redis.asyncio import Redis

from app.config.settings import settings

logger = logging.getLogger(__name__)

redis_client = Redis.from_url(
    str(settings.REDIS_URL),
    decode_responses=True,
)


async def check_redis_health() -> bool:
    """Validates connection to Redis instance."""
    try:
        res = await redis_client.ping()
        return bool(res)
    except Exception as e:
        logger.error(f"Redis healthcheck failed: {e}")
        return False
