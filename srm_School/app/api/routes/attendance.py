from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import List
from datetime import datetime, time
from app.db.database import get_db
from app.models.attendance import Attendance
from app.schemas.attendance import AttendanceCreate, AttendanceOut
from app.core.dependencies import get_current_user
from fastapi import HTTPException

router = APIRouter(prefix="/attendance", tags=["Attendance"])

async def create_attendance(
    data: AttendanceCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user)
):
    school_start = time(8, 0)
    arrival = data.arrival_time.time()
    late = max((datetime.combine(data.date, arrival) - datetime.combine(data.date, school_start)).seconds // 60, 0)

    new_att = Attendance(
        student_id=data.student_id,
        date=data.date,
        arrival_time=arrival,
        late_minutes=late
    )
    db.add(new_att)
    await db.commit()
    await db.refresh(new_att)
    return new_att

@router.get("/", response_model=List[AttendanceOut])
async def get_all_attendance(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user)
):
    result = await db.execute(select(Attendance))
    return result.scalars().all()

@router.get("/{attendance_id}", response_model=AttendanceOut)
async def get_attendance_by_id(
    attendance_id: int,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user)
):
    result = await db.execute(select(Attendance).where(Attendance.id == attendance_id))
    attendance = result.scalar_one_or_none()
    if not attendance:
        raise HTTPException(status_code=404, detail="Attendance not found")
    return attendance

