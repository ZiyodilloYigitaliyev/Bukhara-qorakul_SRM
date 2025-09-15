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
from app.models.chat import ChatRoom, ChatMessage
from app.schemas.chat import ChatRoomOut, ChatMessageOut
from sqlalchemy import select, insert
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.database import get_db
from typing import List
from app.services.student_service import get_week_schedule

router = APIRouter(
    prefix="/student",
    tags=["Mobile - Student"]
)

def make_pair_slug(teacher_id: int, student_id: int) -> str:
    return f"teacher:{teacher_id}__student:{student_id}"


@router.get("/profile", response_model=StudentOut)
async def profile(user=Depends(get_current_student_user)):
    return await get_student_profile(user.id)


@router.get("/schedule/today", response_model=list[ScheduleOut])
async def today_schedule(
    user=Depends(get_current_student_user),
    db: AsyncSession = Depends(get_db),
):
    return await get_today_schedule(user.class_name, user.id, db)

class WeekDayOut(BaseModel):
    day: str
    items: List[ScheduleOut]

@router.get("/schedule/week", response_model=List[WeekDayOut])
async def week_schedule(
    user=Depends(get_current_student_user),
    db: AsyncSession = Depends(get_db),
):
    return await get_week_schedule(user.class_name, user.id, db)

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

@router.post("/chat/room", response_model=ChatRoomOut)
async def student_teacher_room(
    teacher_id: int,
    user=Depends(get_current_student_user),
    db: AsyncSession = Depends(get_db),
):
    slug = make_pair_slug(teacher_id=teacher_id, student_id=user.id)
    res = await db.execute(select(ChatRoom).where(ChatRoom.slug == slug))
    room = res.scalar_one_or_none()
    if not room:
        await db.execute(insert(ChatRoom).values(slug=slug, is_group=False))
        await db.commit()
    return ChatRoomOut(slug=slug)

@router.get("/chat/history", response_model=list[ChatMessageOut])
async def chat_history(
    teacher_id: int,
    limit: int = Query(default=50, ge=1, le=200),
    before_id: int | None = None,
    user=Depends(get_current_student_user),
    db: AsyncSession = Depends(get_db),
):
    slug = make_pair_slug(teacher_id=teacher_id, student_id=user.id)
    q = select(ChatMessage).where(ChatMessage.room_slug == slug)
    if before_id:
        q = q.where(ChatMessage.id < before_id)
    q = q.order_by(ChatMessage.id.desc()).limit(limit)
    rows = (await db.execute(q)).scalars().all()
    # Eng eski → eng yangi tartibda qaytaramiz
    return [ChatMessageOut.model_validate(r) for r in reversed(rows)]
