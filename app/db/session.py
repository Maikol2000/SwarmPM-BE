from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings
from app.db.base import Base

settings = get_settings()

_engine_kwargs: dict = {
    "future": True,
    "pool_pre_ping": True,
}
if settings.database_url.startswith("sqlite"):
    _engine_kwargs["connect_args"] = {"check_same_thread": False}

engine = create_engine(settings.database_url, **_engine_kwargs)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine, expire_on_commit=False)
_db_initialized = False


def init_db() -> None:
    global _db_initialized
    Base.metadata.create_all(bind=engine)
    _db_initialized = True


def get_db() -> Generator[Session, None, None]:
    if not _db_initialized:
        init_db()

    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
