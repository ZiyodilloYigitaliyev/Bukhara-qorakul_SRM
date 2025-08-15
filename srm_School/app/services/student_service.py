# app/services/student_service.py

from datetime import date, timedelta
from sqlalchemy.future import select
from sqlalchemy.orm import joinedload
from app.db.session import async_session
from app.models import Student, Schedule, Score, Attendance
from app.schemas.student import StudentOut
from app.schemas.schedule import ScheduleOut
from app.schemas.score import ScoreOut
from app.schemas.attendance import AttendanceOut


def get_filter_start_date(filter: str) -> date:
    today = date.today()
    if filter == "weekly":
        return today - timedelta(days=7)
    elif filter == "monthly":
        return today.replace(day=1)
    elif filter == "yearly":
        return today.replace(month=1, day=1)
    return today


async def get_student_profile(student_id: int) -> StudentOut:
    async with async_session() as session:
        result = await session.execute(
            select(Student).where(Student.id == student_id)
        )
        student = result.scalar_one()
        return student


async def get_today_schedule(class_name: str) -> list[ScheduleOut]:
    async with async_session() as session:
        weekday = date.today().strftime('%A')
        result = await session.execute(
            select(Schedule).options(joinedload(Schedule.teacher))
            .where(Schedule.class_name == class_name)
            .where(Schedule.day == weekday)
        )
        return result.scalars().all()


async def get_student_scores(student_id: int, filter: str) -> list[ScoreOut]:
    date_from = get_filter_start_date(filter)
    async with async_session() as session:
        result = await session.execute(
            select(Score)
            .where(Score.student_id == student_id)
            .where(Score.date >= date_from)
        )
        return result.scalars().all()


async def get_average_score(student_id: int, filter: str):
    scores = await get_student_scores(student_id, filter)
    if not scores:
        return {"average_score": 0.0}
    avg = round(sum([s.score for s in scores]) / len(scores), 2)
    return {"average_score": avg}


async def get_attendance_records(student_id: int, filter: str) -> list[AttendanceOut]:
    date_from = get_filter_start_date(filter)
    async with async_session() as session:
        result = await session.execute(
            select(Attendance)
            .where(Attendance.student_id == student_id)
            .where(Attendance.date >= date_from)
        )
        return result.scalars().all()


async def get_attendance_percentage(student_id: int, days: int):
    from_date = date.today() - timedelta(days=days)
    async with async_session() as session:
        result = await session.execute(
            select(Attendance)
            .where(Attendance.student_id == student_id)
            .where(Attendance.date >= from_date)
        )
        records = result.scalars().all()
        total = len(records)
        present = sum(1 for r in records if r.is_present)
        percent = round((present / total) * 100, 2) if total else 0
        return {"percentage": percent}


async def get_full_report(student_id: int, filter: str):
    avg_data = await get_average_score(student_id, filter)
    attendance_data = await get_attendance_percentage(student_id, 7 if filter == "weekly" else 30)
    return {
        "average_score": avg_data["average_score"],
        "attendance_percentage": attendance_data["percentage"],
        "bonus_points": 2.5  # optional
    }
