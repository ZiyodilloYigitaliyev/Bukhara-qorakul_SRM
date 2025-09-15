# app/db/session.py
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from app.core.config import settings

engine = create_async_engine(
    settings.ASYNC_DATABASE_URL,   # ✅ har doim postgresql+asyncpg://... bo'ladi (prod-da sslmode=require qo'shiladi)
    echo=False,
    pool_pre_ping=True,
)
async_session = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
