# alembic/env.py
import os
from logging.config import fileConfig
from alembic import context
from sqlalchemy import engine_from_config, pool

# (ixtiyoriy) lokal .env ni yuklash
try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# 1) Faqat Base ni olib kelamiz (bu fayl hech qachon modellardan import qilmasin)
from app.db.base import Base
# 2) MUHIM: Barcha modellarning modullarini yuklaymiz — shunda Base.metadata to‘ladi
import app.models  # noqa: F401  (models/__init__.py ichida Student, Teacher, ... import qilingan bo‘lsin)

target_metadata = Base.metadata


def _to_sync_url(url: str | None) -> str | None:
    if not url:
        return url
    u = url.strip()
    # Heroku classic: postgres:// -> postgresql+psycopg2://
    if u.startswith("postgres://"):
        u = u.replace("postgres://", "postgresql+psycopg2://", 1)
    # postgresql:// (drayversiz) -> postgresql+psycopg2://
    elif u.startswith("postgresql://") and "+psycopg2" not in u and "+asyncpg" not in u:
        u = u.replace("postgresql://", "postgresql+psycopg2://", 1)

    is_local = ("localhost" in u) or ("127.0.0.1" in u)
    if not is_local and "sslmode=" not in u:
        u += ("&" if "?" in u else "?") + "sslmode=require"
    return u


def _get_sync_db_url() -> str:
    # Ustuvor: SYNC_DATABASE_URL -> DATABASE_URL
    sync = os.getenv("SYNC_DATABASE_URL")
    if sync:
        out = _to_sync_url(sync)
        if out:
            return out
    db = os.getenv("DATABASE_URL")
    if db:
        out = _to_sync_url(db)
        if out:
            return out
    raise RuntimeError("DATABASE_URL/SYNC_DATABASE_URL topilmadi (Heroku Config Vars yoki .env dan bering).")


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
    configuration["sqlalchemy.url"] = _get_sync_db_url()

    connectable = engine_from_config(
        configuration, prefix="sqlalchemy.", poolclass=pool.NullPool
    )

    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
