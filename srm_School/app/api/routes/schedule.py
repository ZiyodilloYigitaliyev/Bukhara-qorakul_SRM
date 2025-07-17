from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.schemas.schedule import CreateSchedule, ScheduleOut
from app.core.dependencies import get_db, require_role
from app.crud import schedule as crud_schedule
from app.models.schedule import Schedule
from sqlalchemy.orm import joinedload
from sqlalchemy.future import select
from typing import List

router = APIRouter(prefix="/schedules", tags=["Schedule"])

@router.post("/", response_model=ScheduleOut)
async def create_schedule(
    data: CreateSchedule,
    db: AsyncSession = Depends(get_db),
    user=Depends(require_role("staff", "superuser"))
):
    return await crud_schedule.create_schedule(db, data)

@router.get("/", response_model=list[ScheduleOut])
async def get_all_schedules(
    db: AsyncSession = Depends(get_db),
    user=Depends(require_role("staff", "superuser"))
):
    return await crud_schedule.get_all_schedules(db)

async def get_schedules(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Schedule).options(joinedload(Schedule.teacher))
    )
    schedules = result.scalars().all()
    return schedules

@router.get("/class/{class_name}/{day}", response_model=list[ScheduleOut])
async def get_schedule_by_class(
    class_name: str,
    day: str,
    db: AsyncSession = Depends(get_db),
    user=Depends(require_role("staff", "superuser", "teacher"))
):
    return await crud_schedule.get_schedule_by_class_and_day(db, class_name, day)
