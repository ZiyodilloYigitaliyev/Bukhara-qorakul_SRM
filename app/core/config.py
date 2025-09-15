# app/core/config.py

import os
from typing import Literal, Optional
from pydantic_settings import BaseSettings, SettingsConfigDict
    

def _normalize_db_url(url: Optional[str], driver: Literal["asyncpg", "psycopg2"]) -> Optional[str]:
    """
    Heroku va lokal uchun DB URL ni normallashtiradi:
    - postgres://  -> postgresql+<driver>://
    - postgresql:// -> postgresql+<driver>:// (agar +driver ko'rsatilmagan bo'lsa)
    - Lokal bo'lmasa sslmode=require qo'shiladi (agar yo'q bo'lsa)
    """
    if not url:
        return url

    u = url.strip()

    # 'postgres://' dan boshlansa — Heroku klassik URL'i
    if u.startswith("postgres://"):
        u = u.replace("postgres://", f"postgresql+{driver}://", 1)

    # 'postgresql://' lekin drayver ko'rsatilmagan holat
    elif u.startswith("postgresql://") and "+asyncpg" not in u and "+psycopg2" not in u:
        u = u.replace("postgresql://", f"postgresql+{driver}://", 1)

    # allaqachon drayver bor bo'lsa — o'zgartirmaymiz

    # Lokalmi?
    is_local = ("localhost" in u) or ("127.0.0.1" in u)

    # Uzoq serverlarda SSL majburiy (Heroku)
    if not is_local and "sslmode=" not in u:
        u += ("&" if "?" in u else "?") + "sslmode=require"

    return u


class Settings(BaseSettings):
    # --- App ---
    PROJECT_NAME: str = "BQSRM"
    ENVIRONMENT: Literal["development", "staging", "production"] = "development"
    APP_TIMEZONE: str = "Asia/Tashkent"

    # --- Auth ---
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 43200  # 30 kun

    # --- DB ---
    # Heroku DATABASE_URL (postgres://...) yoki lokal URL
    DATABASE_URL: str
    # (ixtiyoriy) Alembic uchun alohida sync URL berishni xohlasangiz:
    SYNC_DATABASE_URL: Optional[str] = None

    # --- ESKIZ ---
    ESKIZ_BASE_URL: str = "https://notify.eskiz.uz"
    ESKIZ_EMAIL: Optional[str] = None
    ESKIZ_PASSWORD: Optional[str] = None
    ESKIZ_FROM: str = "4546"

    # pydantic-settings (v2) konfiguratsiyasi
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # App (async engine) uchun tayyor URL
    @property
    def ASYNC_DATABASE_URL(self) -> str:
        return _normalize_db_url(self.DATABASE_URL, "asyncpg") or self.DATABASE_URL

    # Alembic (sync engine) uchun tayyor URL
    @property
    def EFFECTIVE_SYNC_DATABASE_URL(self) -> str:
        base = self.SYNC_DATABASE_URL or self.DATABASE_URL
        norm = _normalize_db_url(base, "psycopg2")
        if not norm:
            raise RuntimeError("DATABASE_URL/SYNC_DATABASE_URL topilmadi.")
        return norm


settings = Settings()
