from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.models.schedule import Schedule
from app.schemas.schedule import CreateSchedule

async def create_schedule(db: AsyncSession, data: CreateSchedule):
    schedule = Schedule(**data.dict())
    db.add(schedule)
    await db.commit()
    await db.refresh(schedule)
    return schedule

async def get_all_schedules(db: AsyncSession):
    result = await db.execute(select(Schedule))
    return result.scalars().all()

async def get_schedule_by_class_and_day(db: AsyncSession, class_name: str, day: str):
    result = await db.execute(
        select(Schedule).where(Schedule.class_name == class_name, Schedule.day == day)
    )
    return result.scalars().all()
