from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.models.teacher import Teacher
from app.schemas.teacher import CreateTeacher

async def create_teacher(db: AsyncSession, data: CreateTeacher) -> Teacher:
    teacher = Teacher(**data.dict())
    db.add(teacher)
    await db.commit()
    await db.refresh(teacher)
    return teacher

async def get_all_teachers(db: AsyncSession) -> list[Teacher]:
    result = await db.execute(select(Teacher))
    return list(result.scalars().all())

async def get_teacher_by_id(db: AsyncSession, teacher_id: int) -> Teacher | None:
    result = await db.execute(select(Teacher).where(Teacher.id == teacher_id))
    return result.scalar_one_or_none()
