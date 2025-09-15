import os
from logging.config import fileConfig
from alembic import context
from sqlalchemy import engine_from_config, pool
from app.core.config import settings
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]  # .../Bukhara-qorakul_SRM
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Base + barcha modellarning metadata'sini yuklash
from app.db.base import Base   # Base = declarative_base()
import app.models              # models/__init__.py ichida barcha modellaringiz import qilingan bo'lsin

target_metadata = Base.metadata

def _sync_url() -> str:
    return settings.SYNC_DATABASE_URL  # psycopg2 + sslmode=require (prod)

def run_migrations_offline():
    context.configure(url=_sync_url(), target_metadata=target_metadata, literal_binds=True, dialect_opts={"paramstyle": "named"})
    with context.begin_transaction():
        context.run_migrations()

def run_migrations_online():
    configuration = config.get_section(config.config_ini_section) or {}
    configuration["sqlalchemy.url"] = _sync_url()
    connectable = engine_from_config(configuration, prefix="sqlalchemy.", poolclass=pool.NullPool)
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
