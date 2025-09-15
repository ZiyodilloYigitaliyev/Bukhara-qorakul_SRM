# app/core/config.py
from typing import Optional, Literal
from urllib.parse import urlparse, parse_qsl, urlencode, urlunparse
from pydantic_settings import BaseSettings, SettingsConfigDict

def _set_query_params(u: str, remove: list[str] = None, add: dict[str, str] = None) -> str:
    p = urlparse(u)
    q = dict(parse_qsl(p.query, keep_blank_values=True))
    for k in (remove or []):
        q.pop(k, None)
    if add:
        q.update(add)
    return urlunparse(p._replace(query=urlencode(q, doseq=True)))

def _normalize_db_url(url: Optional[str], driver: Literal["asyncpg", "psycopg2"]) -> Optional[str]:
    if not url:
        return url
    u = url.strip()

    # Prefixni to‘g‘rilash
    if u.startswith("postgres://"):
        u = u.replace("postgres://", f"postgresql+{driver}://", 1)
    elif u.startswith("postgresql://") and "+asyncpg" not in u and "+psycopg2" not in u:
        u = u.replace("postgresql://", f"postgresql+{driver}://", 1)

    is_local = ("localhost" in u) or ("127.0.0.1" in u)

    if not is_local:
        # Prod/Heroku: har ikki drayver uchun ham sslmode=require ishlataymiz
        u = _set_query_params(u, remove=["ssl"], add={"sslmode": "require"})
    else:
        # Lokal: ssl parametrlarini olib tashlaymiz
        u = _set_query_params(u, remove=["sslmode", "ssl"])

    return u

class Settings(BaseSettings):
    PROJECT_NAME: str = "BQSRM"
    ENVIRONMENT: Literal["development","staging","production"] = "development"

    DATABASE_URL: str
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ESKIZ_BASE_URL: str 
    ESKIZ_EMAIL: str
    ESKIZ_PASSWORD: str
    ESKIZ_FROM: str
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    @property
    def ASYNC_DATABASE_URL(self) -> str:
        # App (SQLAlchemy async + asyncpg) uchun
        return _normalize_db_url(self.DATABASE_URL, "asyncpg") or self.DATABASE_URL

    @property
    def SYNC_DATABASE_URL(self) -> str:
        # Alembic (psycopg2) uchun
        return _normalize_db_url(self.DATABASE_URL, "psycopg2") or self.DATABASE_URL

settings = Settings()
