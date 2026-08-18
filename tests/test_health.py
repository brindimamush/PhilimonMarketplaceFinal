import pytest

from app.database.session import check_db_health
from app.utils.redis import check_redis_health


@pytest.mark.asyncio
async def test_database_connection():
    """Verify PostgreSQL connectivity during integration test pass."""
    assert await check_db_health() is True


@pytest.mark.asyncio
async def test_redis_connection():
    """Verify Redis connectivity during integration test pass."""
    assert await check_redis_health() is True
