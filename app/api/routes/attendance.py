# app/api/routes/attendance.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Optional
from datetime import datetime, time, date

from app.db.database import get_db
from app.models.attendance import Attendance
from app.schemas.attendance import AttendanceCreate, AttendanceManualCreate, AttendanceOut
from app.core.dependencies import get_current_user
from app.services.attendance_service import create_attendance_manual

router = APIRouter(prefix="/attendance", tags=["Attendance"])


# (ixtiyoriy) eski helper; agar kerak bo'lmasa olib tashlashingiz mumkin
async def create_attendance(
    data: AttendanceCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user)
):
    school_start = time(8, 0)
    # arrival_time datetime yoki time bo'lishi mumkin
    arrival_dt_or_t = data.arrival_time
    arrival = arrival_dt_or_t.time() if hasattr(arrival_dt_or_t, "time") else arrival_dt_or_t
    late = max(
        (datetime.combine(data.date, arrival) - datetime.combine(data.date, school_start)).seconds // 60,
        0
    )

    new_att = Attendance(
        student_id=data.student_id,
        date=data.date,
        arrival_time=arrival,
        late_minutes=late,
    )
    db.add(new_att)
    await db.commit()
    await db.refresh(new_att)
    # ⚠️ Har doim model_validate bilan qaytaramiz — alias/validatorlar ishlashi uchun
    return AttendanceOut.model_validate(new_att)


@router.get("/by-school", response_model=List[AttendanceOut], response_model_by_alias=True)
async def get_attendance_by_school(
    school_id: int,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    student_id: Optional[int] = None,
    limit: int = 200,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Attendance ro'yxatini maktab bo'yicha filtrlab olish.
    Qo'shimcha filtrlash: date_from, date_to, student_id.
    Pagination: limit/offset.
    """
    conditions = [Attendance.school_id == school_id]
    if date_from:
        conditions.append(Attendance.date >= date_from)
    if date_to:
        conditions.append(Attendance.date <= date_to)
    if student_id:
        conditions.append(Attendance.student_id == student_id)

    stmt = (
        select(Attendance)
        .where(*conditions)  # bir nechta shart -> AND
        .order_by(Attendance.date.desc(), Attendance.id.desc())
        .offset(offset)
        .limit(limit)
    )
    result = await db.execute(stmt)
    rows = result.scalars().all()
    return [AttendanceOut.model_validate(r) for r in rows]

@router.get("/", response_model=List[AttendanceOut], response_model_by_alias=True)
async def get_all_attendance(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user)
):
    result = await db.execute(
        select(Attendance).order_by(Attendance.date.desc(), Attendance.id.desc())
    )
    rows = result.scalars().all()
    # ⚠️ ORM -> Schema (alias/validatorlar ishga tushadi)
    return [AttendanceOut.model_validate(r) for r in rows]


@router.get("/{attendance_id}", response_model=AttendanceOut, response_model_by_alias=True)
async def get_attendance_by_id(
    attendance_id: int,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user)
):
    result = await db.execute(select(Attendance).where(Attendance.id == attendance_id))
    attendance = result.scalar_one_or_none()
    if not attendance:
        raise HTTPException(status_code=404, detail="Attendance not found")
    # ⚠️ ORM -> Schema
    return AttendanceOut.model_validate(attendance)




@router.post("/", response_model=AttendanceOut, response_model_by_alias=True)
async def add_attendance(
    data: AttendanceManualCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    row = await create_attendance_manual(db, data, current_user)
    # ⚠️ ORM -> Schema
    return AttendanceOut.model_validate(row)


@router.delete("/{attendance_id}")
async def delete_attendance_by_id(
    attendance_id: int,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user)
):
    result = await db.execute(select(Attendance).where(Attendance.id == attendance_id))
    attendance = result.scalar_one_or_none()
    if not attendance:
        raise HTTPException(status_code=404, detail="Attendance not found")
    await db.delete(attendance)
    await db.commit()
    return {"detail": "Attendance deleted"}

@router.delete("/")
async def delete_all_attendance(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user)
):
    result = await db.execute(select(Attendance))
    attendances = result.scalars().all()
    if not attendances:
        raise HTTPException(status_code=404, detail="No attendance records found")
    for attendance in attendances:
        await db.delete(attendance)
    await db.commit()
    return {"detail": "All attendance records deleted"}
