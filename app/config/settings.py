from pydantic import Field, PostgresDsn, RedisDsn, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Centralized application settings loaded from environment variables."""

    BOT_TOKEN: str = Field(..., description="Telegram Bot API Token")
    DATABASE_URL: PostgresDsn = Field(
        ..., description="Asyncpg PostgreSQL connection string"
    )
    REDIS_URL: RedisDsn = Field(..., description="Redis connection string")
    ADMIN_TELEGRAM_IDS: list[int] = Field(
        default_factory=list, description="List of Admin Telegram IDs"
    )
    ENVIRONMENT: str = Field(
        "development",
        description="Environment stage: development, staging, production",
    )
    LOG_LEVEL: str = Field("INFO", description="Global logging level")

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    @field_validator("ADMIN_TELEGRAM_IDS", mode="before")
    @classmethod
    def parse_admin_ids(cls, v: object) -> list[int]:
        if isinstance(v, str):
            return [int(x.strip()) for x in v.split(",") if x.strip()]
        if isinstance(v, list):
            return [int(x) for x in v]
        return []


settings = Settings()  # type: ignore[call-arg]
