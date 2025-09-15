from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import date
from typing import List

from app.db.database import get_db
from app.schemas.schedule import ScheduleCreate, ScheduleOut
from app.crud import schedule as crud_schedule


# faqat staff/admin o‘zgartiradi
from app.core.dependencies import get_current_user
def _require_staff_or_admin(user=Depends(get_current_user)):
    if getattr(user, "role", None) not in ("staff","superuser"):
        from fastapi import HTTPException, status
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Ruxsat yo‘q")
    return user

router = APIRouter(prefix="/schedule", tags=["Schedule"])

@router.post("/", response_model=ScheduleOut, dependencies=[Depends(_require_staff_or_admin)])
async def create_schedule(data: ScheduleCreate, db: AsyncSession = Depends(get_db)):
    return await crud_schedule.create_schedule(db, data)

@router.get("/", response_model=List[ScheduleOut], dependencies=[Depends(_require_staff_or_admin)])
async def list_schedules(db: AsyncSession = Depends(get_db)):
    return await crud_schedule.get_all_schedules(db)

# O‘qituvchi bo‘yicha (kun)
@router.get("/teacher/{teacher_id}", response_model=List[ScheduleOut], dependencies=[Depends(_require_staff_or_admin)])
async def teacher_day(teacher_id: int, day: date, db: AsyncSession = Depends(get_db)):
    return await crud_schedule.list_for_teacher_on_date(db, teacher_id, day)

# Student bo‘yicha (kun)
@router.get("/student/{student_id}", response_model=List[ScheduleOut], dependencies=[Depends(_require_staff_or_admin)])
async def student_day(student_id: int, day: date, db: AsyncSession = Depends(get_db)):
    return await crud_schedule.list_for_student_on_date(db, student_id, day)
