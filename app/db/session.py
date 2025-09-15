# app/db/session.py
from urllib.parse import urlparse
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from app.core.config import settings

def _is_local(url: str) -> bool:
    try:
        host = urlparse(url).hostname or ""
    except Exception:
        return False
    return host in {"localhost", "127.0.0.1"}

ASYNC_URL = settings.ASYNC_DATABASE_URL
extra = {}
if not _is_local(ASYNC_URL):
    # Heroku/RDS uchun asyncpg'ga ssl'ni majburan yoqamiz
    extra["connect_args"] = {"ssl": True}

engine = create_async_engine(
    ASYNC_URL,
    echo=False,
    pool_pre_ping=True,
    **extra,
)

async_session = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
