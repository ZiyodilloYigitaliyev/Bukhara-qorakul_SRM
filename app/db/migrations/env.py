# app/db/migrations/env.py
from __future__ import annotations

import sys
from pathlib import Path
from logging.config import fileConfig

from sqlalchemy import create_engine, pool
from alembic import context

# project root to sys.path
ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

config = context.config

# logging (ini bo'lmasa ham yiqilmasin)
try:
    if config.config_file_name:
        fileConfig(config.config_file_name)
except Exception as e:
    print(f"[alembic] logging config skipped: {e}")

from app.core.config import settings
from app.db.base import Base
import app.models  # noqa: F401  # metadata to'lsin

target_metadata = Base.metadata

def run_migrations_offline() -> None:
    url = settings.SYNC_DATABASE_URL  # psycopg2 (+ sslmode=require prod’da)
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        compare_server_default=True,
    )
    with context.begin_transaction():
        context.run_migrations()

def run_migrations_online() -> None:
    connectable = create_engine(
        settings.SYNC_DATABASE_URL,  # MUHIM: SYNC URL
        poolclass=pool.NullPool,
        future=True,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            compare_server_default=True,
        )
        with context.begin_transaction():
            context.run_migrations()

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
