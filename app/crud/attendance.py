# app/crud/attendance.py

import os
from typing import Optional
from datetime import datetime, date as dt_date, time as dt_time

from fastapi import HTTPException
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.attendance import Attendance
from app.models.student import Student
from app.models.teacher import Teacher

# --- Vaqt zonasi (Heroku: heroku config:set TZ=Asia/Samarkand) ---
LOCAL_TZ_NAME = os.getenv("APP_TZ") or os.getenv("TZ") or "Asia/Samarkand"

try:
    from zoneinfo import ZoneInfo
    LOCAL_TZ = ZoneInfo(LOCAL_TZ_NAME)
except Exception:
    # Python <3.9 fallback (agar kerak bo'lsa)
    LOCAL_TZ = None

def _now_local() -> datetime:
    if LOCAL_TZ is None:
        return datetime.now()
    return datetime.now(LOCAL_TZ)

# --- Maktab dars boshlanish vaqti: env orqali moslashuvchan ---
def _parse_cutoff(s: str) -> dt_time:
    hh, mm = s.split(":")
    return dt_time(int(hh), int(mm))

LATE_CUTOFF = _parse_cutoff(os.getenv("LATE_CUTOFF", "08:00"))  # default 08:00


def _normalize_time(value) -> dt_time:
    """
    value datetime yoki time bo'lishi mumkin (hatto "HH:MM" string bo'lsa ham).
    """
    if value is None:
        now = _now_local()
        return dt_time(now.hour, now.minute)
    if isinstance(value, dt_time):
        return value
    if isinstance(value, datetime):
        return value.time()
    if isinstance(value, str):
        try:
            hh, mm = value.split(":")
            return dt_time(int(hh), int(mm))
        except Exception:
            raise HTTPException(400, "time_str/arrival_time noto‘g‘ri format (kutilgan: 'HH:MM')")
    raise HTTPException(400, "Vaqt maydoni noto‘g‘ri turda yuborildi")


def _calc_late(arrival: dt_time) -> tuple[str, int]:
    """
    arrival_status, late_minutes
    """
    if arrival <= LATE_CUTOFF:
        return "on_time", 0
    mins = (arrival.hour - LATE_CUTOFF.hour) * 60 + (arrival.minute - LATE_CUTOFF.minute)
    return "late", mins


async def _upsert_daily_row(
    db: AsyncSession,
    *,
    student_id: Optional[int],
    teacher_id: Optional[int],
    day: dt_date,
    school_id: Optional[int],
) -> Attendance:
    q = select(Attendance).where(
        and_(
            Attendance.date == day,
            Attendance.student_id == (student_id if student_id is not None else None),
            Attendance.teacher_id == (teacher_id if teacher_id is not None else None),
        )
    )
    row = await db.scalar(q)
    if row:
        return row

    row = Attendance(
        date=day,
        student_id=student_id,
        teacher_id=teacher_id,
        is_present=True,
        school_id=school_id,
        user_type="student" if student_id else "teacher",
    )
    db.add(row)
    await db.flush()
    return row


# --------------------------
#  MANUAL: IN / OUT / EXCUSED / ABSENT
# --------------------------
# Eslatma: bu CRUD funksiyasi sizning "manual" schema (AttendanceManualCreate) bilan ishlaydi.
# Agar eski AttendanceCreate bo'lsa, frontend/service qatlamida moslab yuboring.

async def mark_attendance_manual(
    db: AsyncSession,
    *,
    student_id: Optional[int],
    teacher_id: Optional[int],
    action: str,                   # "IN" | "OUT" | "EXCUSED" | "ABSENT"
    date: Optional[dt_date] = None,
    time_value: Optional[object] = None,   # datetime | time | "HH:MM" | None
    late_override: Optional[int] = None,
    status: Optional[str] = None,
    school_id: Optional[int] = None,
):
    # 1) kim uchun?
    if not student_id and not teacher_id:
        raise HTTPException(400, "student_id yoki teacher_id dan biri kerak")
    if student_id and teacher_id:
        raise HTTPException(400, "faqat bittasini yuboring: student_id yoki teacher_id")

    # 2) mavjudligini tekshirish (ixtiyoriy, ammo foydali)
    if student_id:
        exists = await db.scalar(select(Student.id).where(Student.id == student_id))
        if not exists:
            raise HTTPException(404, "Student topilmadi")
    if teacher_id:
        exists = await db.scalar(select(Teacher.id).where(Teacher.id == teacher_id))
        if not exists:
            raise HTTPException(404, "Teacher topilmadi")

    # 3) server TZ bo‘yicha sana/vaqt
    day = date or _now_local().date()
    tm: dt_time = _normalize_time(time_value)

    # 4) kunlik satrni topish/yaratish
    row = await _upsert_daily_row(
        db,
        student_id=student_id,
        teacher_id=teacher_id,
        day=day,
        school_id=school_id,
    )

    # 5) action bo‘yicha
    a = action.upper()
    if a == "IN":
        row.arrival_time = tm
        if late_override is not None:
            row.late_minutes = max(0, int(late_override))
            row.arrival_status = "late" if row.late_minutes > 0 else "on_time"
        else:
            row.arrival_status, row.late_minutes = _calc_late(tm)
        row.is_present = True
        if status:
            row.status = status[:20]

    elif a == "OUT":
        row.departure_time = tm
        row.is_present = True
        row.status = (status or "left")[:20]

    elif a == "EXCUSED":
        # javob so'rab ketdi — vaqt berilgan bo‘lsa OUT sifatida ham belgilab qo‘yish mumkin
        if time_value is not None:
            row.departure_time = tm
        row.is_present = True
        row.status = "excused"

    elif a == "ABSENT":
        row.is_present = False
        row.arrival_status = None
        row.late_minutes = 0
        row.status = "absent"
        # qat'iy bo‘lishni istasangiz:
        # row.arrival_time = None
        # row.departure_time = None

    else:
        raise HTTPException(400, "Noto‘g‘ri action (IN/OUT/EXCUSED/ABSENT)")

    await db.commit()
    await db.refresh(row)
    return row


# --------------------------
#  READING (student/teacher bo'yicha)
# --------------------------

async def get_attendance_by_student(
    db: AsyncSession,
    student_id: int,
    from_date: Optional[dt_date] = None,
    to_date: Optional[dt_date] = None
):
    stmt = select(Attendance).where(Attendance.student_id == student_id)
    if from_date:
        stmt = stmt.where(Attendance.date >= from_date)
    if to_date:
        stmt = stmt.where(Attendance.date <= to_date)
    result = await db.execute(stmt.order_by(Attendance.date.desc()))
    return result.scalars().all()


async def get_attendance_by_teacher(
    db: AsyncSession,
    teacher_id: int,
    from_date: Optional[dt_date] = None,
    to_date: Optional[dt_date] = None
):
    stmt = select(Attendance).where(Attendance.teacher_id == teacher_id)
    if from_date:
        stmt = stmt.where(Attendance.date >= from_date)
    if to_date:
        stmt = stmt.where(Attendance.date <= to_date)
    result = await db.execute(stmt.order_by(Attendance.date.desc()))
    return result.scalars().all()


# --------------------------
#  DELETE (kunlik satrni o'chirish)
# --------------------------

async def delete_attendance(
    db: AsyncSession,
    *,
    student_id: Optional[int] = None,
    teacher_id: Optional[int] = None,
    day: Optional[dt_date] = None,
):
    if not day:
        raise HTTPException(400, "day (date) kerak")
    if not student_id and not teacher_id:
        raise HTTPException(400, "student_id yoki teacher_id dan biri kerak")
    if student_id and teacher_id:
        raise HTTPException(400, "faqat bittasini yuboring: student_id yoki teacher_id")

    stmt = select(Attendance).where(
        and_(
            Attendance.date == day,
            Attendance.student_id == (student_id if student_id is not None else None),
            Attendance.teacher_id == (teacher_id if teacher_id is not None else None),
        )
    )
    row = await db.scalar(stmt)
    if row:
        await db.delete(row)
        await db.commit()
        return {"detail": "Attendance record deleted."}
    return {"detail": "Attendance record not found."}

async def get_student_attendance(
    db: AsyncSession,
    student_id: int,
    from_date: Optional[dt_date] = None,
    to_date: Optional[dt_date] = None
):
    return await get_attendance_by_student(db, student_id, from_date, to_date)