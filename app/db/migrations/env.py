# alembic/env.py
import os
from alembic import context
from sqlalchemy import engine_from_config, pool
from logging.config import fileConfig
from app.core.config import settings
# (ixtiyoriy) .env ni avtomatik yuklash (local uchun qulay)
try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# <-- Sizning metadata importingiz (yo'lini loyihangizga moslang)
# masalan: app/db/base.py ichida Base = declarative_base() va barcha modellarga importlar bor
from app.db.base import Base  # <-- shu yo'lni loyihangizga qarab to'g'rilang

target_metadata = Base.metadata


def _to_sync_url(url: str | None) -> str | None:
    """
    Heroku va lokal uchun sync (psycopg2) URL yasash:
    - postgres://  -> postgresql+psycopg2://
    - postgresql+asyncpg:// -> postgresql+psycopg2://
    - sslmode=require ni faqat lokal bo'lmaganda qo'shish
    """
    if not url:
        return url

    u = url
    if u.startswith("postgres://"):
        u = u.replace("postgres://", "postgresql+psycopg2://", 1)
    if u.startswith("postgresql+asyncpg://"):
        u = u.replace("postgresql+asyncpg://", "postgresql+psycopg2://", 1)

    is_local = ("localhost" in u) or ("127.0.0.1" in u)
    if (not is_local) and ("sslmode=" not in u):
        u += ("&" if "?" in u else "?") + "sslmode=require"
    return u


def _get_sync_db_url() -> str:
    """
    Ustuvorlik:
    1) SYNC_DATABASE_URL (agar berilgan bo'lsa)
    2) DATABASE_URL (Heroku beradigan) -> sync ga aylantiramiz
    3) Aks holda xato
    """
    sync_url = os.getenv("SYNC_DATABASE_URL")
    if sync_url:
        result = _to_sync_url(sync_url)
        if result is not None:
            return result

    db_url = os.getenv("DATABASE_URL")
    if db_url:
        result = _to_sync_url(db_url)
        if result is not None:
            return result

    raise RuntimeError(
        "DATABASE_URL yoki SYNC_DATABASE_URL topilmadi. "
        "Lokalda .env ichida yoki OS env sifatida bering."
    )


def run_migrations_offline():
    url = _get_sync_db_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    configuration = config.get_section(config.config_ini_section) or {}
    configuration["sqlalchemy.url"] = settings.EFFECTIVE_SYNC_DATABASE_URL

    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
