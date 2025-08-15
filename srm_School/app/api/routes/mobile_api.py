# app/api/routes/mobile_api.py

from fastapi import APIRouter, Depends, Query
from app.core.dependencies import get_current_student_user
from app.services.student_service import (
    get_student_profile,
    get_today_schedule,
    get_student_scores,
    get_average_score,
    get_attendance_records,
    get_attendance_percentage,
    get_full_report,
)
from app.schemas.student import StudentOut
from app.schemas.schedule import ScheduleOut
from app.schemas.score import ScoreOut
from app.schemas.attendance import AttendanceOut
from pydantic import BaseModel

router = APIRouter(
    prefix="/student",
    tags=["Mobile - Student"]
)


@router.get("/profile", response_model=StudentOut)
async def profile(user=Depends(get_current_student_user)):
    return await get_student_profile(user.id)


@router.get("/schedule/today", response_model=list[ScheduleOut])
async def today_schedule(user=Depends(get_current_student_user)):
    return await get_today_schedule(user.class_name)


@router.get("/scores", response_model=list[ScoreOut])
async def get_scores(
    filter: str = Query(default="weekly", enum=["weekly", "monthly", "yearly"]),
    user=Depends(get_current_student_user)
):
    return await get_student_scores(user.id, filter)


@router.get("/scores/average")
async def average_score(
    filter: str = Query(default="weekly", enum=["weekly", "monthly", "yearly"]),
    user=Depends(get_current_student_user)
):
    return await get_average_score(user.id, filter)


@router.get("/attendance", response_model=list[AttendanceOut])
async def get_attendance(
    filter: str = Query(default="weekly", enum=["weekly", "monthly", "yearly"]),
    user=Depends(get_current_student_user)
):
    return await get_attendance_records(user.id, filter)


@router.get("/attendance/percentage")
async def attendance_percent(
    days: int = Query(default=7),
    user=Depends(get_current_student_user)
):
    return await get_attendance_percentage(user.id, days)


@router.get("/report")
async def get_report(
    filter: str = Query(default="monthly", enum=["weekly", "monthly", "yearly"]),
    user=Depends(get_current_student_user)
):
    return await get_full_report(user.id, filter)
