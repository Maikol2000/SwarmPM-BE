import os
from functools import lru_cache


class Settings:
    app_name: str = "SwarmPM Mike Backend"
    database_url: str = os.getenv("DATABASE_URL", "postgresql+psycopg://postgres@localhost:5432/postgres")
    redis_url: str | None = os.getenv("REDIS_URL")
    jwt_secret: str = os.getenv("JWT_SECRET", "dev-secret-change-me")
    jwt_algorithm: str = os.getenv("JWT_ALGORITHM", "HS256")
    oidc_issuer: str | None = os.getenv("OIDC_ISSUER")
    oidc_audience: str | None = os.getenv("OIDC_AUDIENCE")
    access_token_expire_minutes: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "120"))
    allow_legacy_dev_token: bool = os.getenv("ALLOW_LEGACY_DEV_TOKEN", "true").lower() == "true"
    service_token_expire_minutes: int = int(os.getenv("SERVICE_TOKEN_EXPIRE_MINUTES", "15"))
    core_logic_transport: str = os.getenv("CORE_LOGIC_TRANSPORT", "inprocess")
    core_logic_grpc_target: str = os.getenv("CORE_LOGIC_GRPC_TARGET", "127.0.0.1:50051")
    start_embedded_core_logic_grpc: bool = os.getenv("START_EMBEDDED_CORE_LOGIC_GRPC", "false").lower() == "true"
    embedded_core_logic_grpc_bind: str = os.getenv("EMBEDDED_CORE_LOGIC_GRPC_BIND", "127.0.0.1:50051")
    gateway_rate_limit_window_seconds: int = int(os.getenv("GATEWAY_RATE_LIMIT_WINDOW_SECONDS", "60"))
    gateway_rate_limit_requests: int = int(os.getenv("GATEWAY_RATE_LIMIT_REQUESTS", "120"))


@lru_cache
def get_settings() -> Settings:
    return Settings()
