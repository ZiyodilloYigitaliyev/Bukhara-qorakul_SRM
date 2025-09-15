# app/core/config.py
from typing import Optional, Literal
from urllib.parse import urlparse, parse_qsl, urlencode, urlunparse
import re
from pydantic_settings import BaseSettings, SettingsConfigDict

def _set_qs(u: str, remove=None, add=None) -> str:
    p = urlparse(u); q = dict(parse_qsl(p.query, keep_blank_values=True))
    for k in (remove or []): q.pop(k, None)
    if add: q.update(add)
    return urlunparse(p._replace(query=urlencode(q, doseq=True)))

def _force_driver(u: str, driver: Literal["asyncpg","psycopg2"]) -> str:
    # postgres://  -> postgresql+<driver>://
    u = re.sub(r"^postgres://", f"postgresql+{driver}://", u)
    # postgresql://, postgresql+asyncpg://, postgresql+psycopg2:// -> postgresql+<driver>://
    u = re.sub(r"^postgresql(\+\w+)?://", f"postgresql+{driver}://", u)
    return u

def _norm(url: Optional[str], driver: Literal["asyncpg","psycopg2"]) -> Optional[str]:
    if not url:
        return url
    u = _force_driver(url.strip(), driver)
    is_local = ("localhost" in u) or ("127.0.0.1" in u)
    if is_local:
        # local: SSL param yo'q
        u = _set_qs(u, remove=["ssl","sslmode"])
    else:
        # prod (Heroku / RDS): asyncpg -> ssl=true, psycopg2 -> sslmode=require
        if driver == "psycopg2":
            u = _set_qs(u, remove=["ssl"], add={"sslmode": "require"})
        else:
            u = _set_qs(u, remove=["sslmode"], add={"ssl": "true"})
    return u

class Settings(BaseSettings):
    PROJECT_NAME: str = "BQSRM"
    ENVIRONMENT: Literal["development","staging","production"] = "development"

    DATABASE_URL: str
    SECRET_KEY: str
    ALGORITHM: str = "HS256"

    # Eskiz
    ESKIZ_BASE_URL: str
    ESKIZ_EMAIL: str
    ESKIZ_PASSWORD: str
    ESKIZ_FROM: str

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def ASYNC_DATABASE_URL(self) -> str:   # FastAPI app (asyncpg)
        return _norm(self.DATABASE_URL, "asyncpg") or self.DATABASE_URL

    @property
    def SYNC_DATABASE_URL(self) -> str:    # Alembic (psycopg2)
        return _norm(self.DATABASE_URL, "psycopg2") or self.DATABASE_URL

settings = Settings()
