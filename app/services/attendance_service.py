# app/services/attendance_service.py

import os
from datetime import datetime, date as dt_date, time as dt_time
from typing import Optional

from fastapi import HTTPException
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.attendance import Attendance
from app.models.student import Student
from app.models.teacher import Teacher

# --- Timezone (Heroku: heroku config:set TZ=Asia/Samarkand) ---
try:
    from zoneinfo import ZoneInfo
    LOCAL_TZ = ZoneInfo(os.getenv("APP_TZ") or os.getenv("TZ") or "Asia/Samarkand")
except Exception:
    LOCAL_TZ = None  # fallback: naive

# Kechikish kesimi (env orqali ham boshqarish mumkin: LATE_CUTOFF="08:00")
def _parse_cutoff(val: str) -> dt_time:
    hh, mm = val.split(":")
    return dt_time(int(hh), int(mm))

LATE_CUTOFF = _parse_cutoff(os.getenv("LATE_CUTOFF", "08:00"))


def _now_local() -> datetime:
    return datetime.now(LOCAL_TZ) if LOCAL_TZ else datetime.now()


def _normalize_time(raw_time: Optional[object]) -> dt_time:
    """
    raw_time -> datetime.time
    Qabul qiladi: None | "HH:MM" | datetime | time
    None bo'lsa: hozirgi mahalliy vaqt (sekundsuz).
    """
    if raw_time is None:
        now = _now_local()
        return dt_time(now.hour, now.minute)

    if isinstance(raw_time, dt_time):
        return raw_time

    if isinstance(raw_time, datetime):
        t = raw_time.time()
        return dt_time(t.hour, t.minute)

    if isinstance(raw_time, str):
        # "HH:MM" yoki "HH:MM:SS"
        try:
            t = dt_time.fromisoformat(raw_time)
            return dt_time(t.hour, t.minute)
        except ValueError:
            try:
                h, m = map(int, raw_time.split(":")[:2])
                return dt_time(hour=h, minute=m)
            except Exception:
                raise HTTPException(400, "Vaqt noto'g'ri formatda (kutilgan: 'HH:MM')")

    raise HTTPException(400, "Vaqt maydoni noto'g'ri turda yuborildi")


def _calc_late(arrival: dt_time) -> tuple[str, int]:
    """
    return: (arrival_status, late_minutes)
    """
    if arrival <= LATE_CUTOFF:
        return "on_time", 0
    mins = (arrival.hour - LATE_CUTOFF.hour) * 60 + (arrival.minute - LATE_CUTOFF.minute)
    return "late", mins


def _safe_get(data, *names, default=None):
    """
    Pydantic v2 modelidan bir nechta nom orqali birinchi mavjud (None bo'lmagan) qiymatni oladi.
    Maydon umuman bo'lmasa ham xatoga tushmaydi.
    """
    for n in names:
        try:
            v = getattr(data, n)
        except AttributeError:
            continue
        if v is not None:
            return v
    return default


async def _upsert_daily_row(
    db: AsyncSession,
    *,
    student_id: Optional[int],
    teacher_id: Optional[int],
    day: dt_date,
    school_id: Optional[int],
) -> Attendance:
    """
    Kun (date) + (student yoki teacher) bo'yicha bitta satrni topadi yoki yaratadi.
    """
    stmt = select(Attendance).where(
        and_(
            Attendance.date == day,
            Attendance.student_id == (student_id if student_id is not None else None),
            Attendance.teacher_id == (teacher_id if teacher_id is not None else None),
        )
    )
    row = await db.scalar(stmt)
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


async def create_attendance_manual(
    db: AsyncSession,
    data,  # AttendanceManualCreate yoki o'xshash
    current_user,
) -> Attendance:
    # 1) Kim uchun?
    student_id = _safe_get(data, "student_id")
    teacher_id = _safe_get(data, "teacher_id")

    if not student_id and not teacher_id:
        raise HTTPException(400, "student_id yoki teacher_id dan biri kerak")
    if student_id and teacher_id:
        raise HTTPException(400, "faqat bittasini yuboring: student_id yoki teacher_id")

    # Mavjudligini tekshirish (foydali)
    if student_id:
        ok = await db.scalar(select(Student.id).where(Student.id == student_id))
        if not ok:
            raise HTTPException(404, "Student topilmadi")
    if teacher_id:
        ok = await db.scalar(select(Teacher.id).where(Teacher.id == teacher_id))
        if not ok:
            raise HTTPException(404, "Teacher topilmadi")

    # 2) Sana/vaqt: date | day | attendance_date va time_str | time | arrival_time | departure_time
    day: dt_date = _safe_get(data, "date", "day", "attendance_date") or _now_local().date()
    raw_time = _safe_get(data, "time_str", "time", "arrival_time", "departure_time")
    tm: dt_time = _normalize_time(raw_time)

    # 3) Parametrlar
    action = (_safe_get(data, "action", default="IN") or "IN").upper()
    school_id = _safe_get(data, "school_id")
    status_in = _safe_get(data, "status")
    late_override = _safe_get(data, "late_override", "minutes_late", "late_minutes")

    # 4) Kunlik satrni topish/yaratish
    row = await _upsert_daily_row(
        db,
        student_id=student_id,
        teacher_id=teacher_id,
        day=day,
        school_id=school_id,
    )

    # 5) Action bo'yicha
    if action == "IN":
        row.arrival_time = tm
        if late_override is not None:
            row.late_minutes = max(0, int(late_override))
            row.arrival_status = "late" if row.late_minutes > 0 else "on_time"
        else:
            row.arrival_status, row.late_minutes = _calc_late(tm)
        row.is_present = True
        if status_in:
            row.status = str(status_in)[:20]

    elif action == "OUT":
        row.departure_time = tm
        row.is_present = True
        row.status = (status_in or "left")[:20]

    elif action == "EXCUSED":
        # Javob so'rab ketdi — vaqt yuborilgan bo'lsa OUT sifatida ham belgilaymiz
        if raw_time is not None:
            row.departure_time = tm
        row.is_present = True
        row.status = "excused"

    elif action == "ABSENT":
        row.is_present = False
        row.arrival_status = None
        row.late_minutes = 0
        row.status = "absent"
        # qat'iy siyosat bo'lsa, shu qatorlarni yoqing:
        # row.arrival_time = None
        # row.departure_time = None

    else:
        raise HTTPException(400, "Noto‘g‘ri action (IN/OUT/EXCUSED/ABSENT)")

    await db.commit()
    await db.refresh(row)
    return row
