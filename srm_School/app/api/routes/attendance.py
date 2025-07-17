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

@router.post("/", response_model=AttendanceOut)
async def create_attendance(
    data: AttendanceCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user)
):
    # 1. Maktab ochilish vaqti (08:00)
    school_start_time = time(8, 0)

    # 2. Kelgan vaqtni faqat vaqt qismini olish
    arrival_time = data.arrival_time.time()
    
    # 3. Kech qolgan daqiqalarni hisoblash
    late_minutes = 0
    if arrival_time > school_start_time:
        delta = datetime.combine(data.date, arrival_time) - datetime.combine(data.date, school_start_time)
        late_minutes = delta.seconds // 60

    # 4. Yangi Attendance obyektini yaratish
    new_attendance = Attendance(
        student_id=data.student_id,
        date=data.date,
        arrival_time=arrival_time,
        late_minutes=late_minutes
    )

    db.add(new_attendance)
    await db.commit()
    await db.refresh(new_attendance)
    return new_attendance

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

