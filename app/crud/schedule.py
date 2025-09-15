from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_
from fastapi import HTTPException
from app.models.schedule import Schedule
from app.models.student import Student
from app.schemas.schedule import ScheduleCreate
# from app.utils.timezone import UZ  # oldingi vaqt utilingizdan

async def create_schedule(db: AsyncSession, data: ScheduleCreate) -> Schedule:
    item = Schedule(**data.model_dump())
    db.add(item)
    try:
        await db.commit()
        await db.refresh(item)
        return item
    except Exception as e:
        await db.rollback()
        # Unique / FK xatolarini bir xil tutish kifoya
        raise HTTPException(status_code=400, detail="Schedule yaratib bo‘lmadi")

async def list_for_teacher_on_date(db: AsyncSession, teacher_id: int, for_date) -> list[Schedule]:
    # for_date — date (UZ bo‘yicha haftaning kuni)
    dow = for_date.isoweekday()  # 1..7
    res = await db.execute(
        select(Schedule).where(
            Schedule.teacher_id == teacher_id,
            Schedule.day_of_week == dow
        ).order_by(Schedule.start_time)
    )
    return res.scalars().all()

async def list_for_student_on_date(db: AsyncSession, student_id: int, for_date) -> list[Schedule]:
    dow = for_date.isoweekday()
    # student class_id ni olib filterlaymiz
    st = await db.get(Student, student_id)
    if not st:
        raise HTTPException(status_code=404, detail="Student topilmadi")
    res = await db.execute(
        select(Schedule).where(
            Schedule.day_of_week == dow,
            or_(
                Schedule.student_id == student_id,
                Schedule.class_id == st.class_id
            )
        ).order_by(Schedule.start_time)
    )
    return res.scalars().all()

async def get_all_schedules(db: AsyncSession) -> list[Schedule]:
    res = await db.execute(
        select(Schedule).order_by(Schedule.day_of_week, Schedule.start_time)
    )
    return res.scalars().all()