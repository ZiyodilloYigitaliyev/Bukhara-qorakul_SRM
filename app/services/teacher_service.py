from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.teacher import Teacher  # sizda manzili boshqacha bo‘lsa moslang

async def get_teacher_by_login(db: AsyncSession, login: str) -> Teacher | None:
    q = select(Teacher).where(Teacher.login == login)
    res = await db.execute(q)
    return res.scalar_one_or_none()

async def get_teacher_by_id(db: AsyncSession, teacher_id: int) -> Teacher | None:
    q = select(Teacher).where(Teacher.id == teacher_id)
    res = await db.execute(q)
    return res.scalar_one_or_none()
