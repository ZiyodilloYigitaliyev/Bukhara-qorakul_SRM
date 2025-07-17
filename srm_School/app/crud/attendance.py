from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from datetime import time
from app.models.attendance import Attendance
from app.schemas.attendance import AttendanceCreate

SCHOOL_START_TIME = time(hour=8, minute=0)

def calculate_late_minutes(arrival_time: time) -> tuple[str, int | None]:
    if arrival_time <= SCHOOL_START_TIME:
        return "present", None
    delta = (arrival_time.hour * 60 + arrival_time.minute) - (SCHOOL_START_TIME.hour * 60 + SCHOOL_START_TIME.minute)
    return "late", delta

async def mark_attendance(db: AsyncSession, data: AttendanceCreate):
    status = "absent"
    late_minutes = None

    if data.arrival_time:
        arrival_time = data.arrival_time.time() if hasattr(data.arrival_time, "time") else data.arrival_time
        status, late_minutes = calculate_late_minutes(arrival_time)

    attendance = Attendance(
        student_id=data.student_id,
        date=data.date,
        arrival_time=data.arrival_time,
        status=status,
        late_minutes=late_minutes,
        source=data.source,
    )
    db.add(attendance)
    await db.commit()
    await db.refresh(attendance)
    return attendance

async def get_attendance_by_student(db: AsyncSession, student_id: int, from_date=None, to_date=None):
    query = select(Attendance).where(Attendance.student_id == student_id)
    if from_date:
        query = query.where(Attendance.date >= from_date)
    if to_date:
        query = query.where(Attendance.date <= to_date)
    result = await db.execute(query.order_by(Attendance.date.desc()))
    return result.scalars().all()

async def get_student_attendance(db: AsyncSession, student_id: int, start_date=None, end_date=None):
    stmt = select(Attendance).where(Attendance.student_id == student_id)
    if start_date:
        stmt = stmt.where(Attendance.date >= start_date)
    if end_date:
        stmt = stmt.where(Attendance.date <= end_date)
    result = await db.execute(stmt)
    return result.scalars().all()
