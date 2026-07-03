import os
from functools import lru_cache


class Settings:
    app_name: str = "SwarmPM Mike Backend"
    database_url: str = os.getenv("DATABASE_URL", "postgresql+psycopg://postgres@localhost:5432/postgres")
    redis_url: str | None = os.getenv("REDIS_URL")
    jwt_secret: str = os.getenv("JWT_SECRET", "dev-secret-change-me")
    jwt_algorithm: str = os.getenv("JWT_ALGORITHM", "HS256")
    access_token_expire_minutes: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "120"))
    allow_legacy_dev_token: bool = os.getenv("ALLOW_LEGACY_DEV_TOKEN", "true").lower() == "true"


@lru_cache
def get_settings() -> Settings:
    return Settings()
