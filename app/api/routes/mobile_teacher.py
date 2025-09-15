from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from datetime import datetime, date
from passlib.context import CryptContext
from pydantic import BaseModel
from typing import List
from app.db.database import get_db
from app.core.config import settings
from app.core.security import create_access_token

from app.models.teacher import Teacher           
from app.models.schedule import Schedule        
from app.models.student import Student           
from app.models.score import Score               
from app.models.chat import ChatRoom, ChatMessage  

from app.schemas.teacher_mobile import (
    TeacherLogin, TokenOut, TeacherProfileOut, TeacherScoreCreate, TeacherScoreOut,
    TeacherScheduleOut, ChatRoomOut, ChatMessageOut
)

router = APIRouter(prefix="/teacher", tags=["Mobile - Teacher"])
pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")

# # ---- Login (faqat mobil token) ----
# @router.post("/login", response_model=TokenOut)
# async def login_teacher(data: TeacherLogin, db: AsyncSession = Depends(get_db)):
#     q = await db.execute(select(Teacher).where(Teacher.login == data.login))
#     teacher = q.scalar_one_or_none()
#     if not teacher or not pwd_ctx.verify(data.password, teacher.hashed_password):
#         raise HTTPException(status_code=400, detail="Login yoki parol xato")

#     # mobil uchun aud="mobile"
#     access_token = create_access_token(
#         data={"sub": str(teacher.id), "role": "teacher", "aud": "mobile"},
#         expires_minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
#     )
#     return TokenOut(
#         access_token=access_token,
#         token_type="bearer",
#         expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
#     )

# ---- Auth helper: current teacher ----
from app.core.dependencies import get_current_user
async def get_current_teacher(user=Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> Teacher:
    if not user or getattr(user, "role", None) != "teacher":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Teacher only")
    # Agar sizda user.id == teacher.id bo'lmasa, moslab o'zgartiring
    q = await db.execute(select(Teacher).where(Teacher.id == user.id))
    teacher = q.scalar_one_or_none()
    if not teacher:
        raise HTTPException(status_code=404, detail="Teacher topilmadi")
    return teacher

# ---- Profile ----
@router.get("/profile", response_model=TeacherProfileOut)
async def profile(teacher: Teacher = Depends(get_current_teacher)):
    return TeacherProfileOut(
        id=teacher.id,
        first_name=teacher.first_name,
        last_name=teacher.last_name,
        subject=getattr(teacher, "subject", None),
        phone=getattr(teacher, "phone", None)
    )

DAYS = ["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"]

class TeacherWeekDayOut(BaseModel):
    day: str
    items: List[TeacherScheduleOut]

@router.get("/schedule/week", response_model=List[TeacherWeekDayOut])
async def week_schedule(
    db: AsyncSession = Depends(get_db),
    teacher: Teacher = Depends(get_current_teacher),
):
    out: list[TeacherWeekDayOut] = []
    for day in DAYS:
        q = (
            select(Schedule)
            .where(Schedule.teacher_id == teacher.id)
            .where(Schedule.day == day)
            .order_by(Schedule.start_time)
        )
        rows = (await db.execute(q)).scalars().all()
        out.append(TeacherWeekDayOut(
            day=day,
            items=[
                TeacherScheduleOut(
                    class_name=i.class_name,
                    subject=i.subject,
                    start_time=i.start_time,
                    end_time=i.end_time,
                    room=getattr(i, "room", None)
                )
                for i in rows
            ]
        ))
    return out

# ---- Bugungi jadval ----
@router.get("/schedule/today", response_model=list[TeacherScheduleOut])
async def today_schedule(
    db: AsyncSession = Depends(get_db),
    teacher: Teacher = Depends(get_current_teacher)
):
    today_name = date.today().strftime("%A")  # "Monday" ...
    q = (
        select(Schedule)
        .where(Schedule.teacher_id == teacher.id)
        .where(Schedule.day == today_name)
        .order_by(Schedule.start_time)
    )
    res = await db.execute(q)
    items = res.scalars().all()
    return [
        TeacherScheduleOut(
            class_name=i.class_name,
            subject=i.subject,
            start_time=i.start_time,
            end_time=i.end_time,
            room=getattr(i, "room", None)
        )
        for i in items
    ]

# ---- Baho qo‘yish (kunlik 4.5 limiti, yakshanba bonus 2.5) ----
@router.post("/scores", response_model=TeacherScoreOut)
async def give_score(payload: TeacherScoreCreate, db: AsyncSession = Depends(get_db), teacher: Teacher = Depends(get_current_teacher)):
    # student mavjudligini tekshirish
    st_res = await db.execute(select(Student).where(Student.id == payload.student_id))
    student = st_res.scalar_one_or_none()
    if not student:
        raise HTTPException(status_code=404, detail="Student topilmadi")

    today = date.today()
    # bugungi umumiy ball
    sum_q = await db.execute(
        select(func.coalesce(func.sum(Score.value), 0.0))
        .where(Score.student_id == student.id)
        .where(func.date(Score.created_at) == today)
    )
    today_sum = float(sum_q.scalar_one())
    new_total = today_sum + payload.value

    # bonus qoidasi: yakshanba (weekday=6) va bonus=True bo'lsa, value aynan 2.5 bo'lsin
    is_sunday = datetime.utcnow().weekday() == 6
    if payload.bonus:
        if not is_sunday or abs(payload.value - 2.5) > 1e-6:
            raise HTTPException(status_code=400, detail="Bonus faqat yakshanba va 2.5 ball bo'lishi kerak")

    # odatdagi limit 4.5
    if not payload.bonus and new_total > 4.5 + 1e-9:
        raise HTTPException(status_code=400, detail=f"Bugungi limit (4.5) oshib ketadi. Hozirgi: {today_sum}")

    obj = Score(
        student_id=student.id,
        subject=payload.subject,
        value=payload.value,
        teacher_id=teacher.id,
        comment=payload.comment
    )
    db.add(obj)
    await db.commit()
    await db.refresh(obj)

    return TeacherScoreOut(
        id=obj.id,
        student_id=obj.student_id,
        subject=obj.subject,
        value=obj.value,
        created_at=obj.created_at
    )

# ---- Chat: room yaratish/olish (1:1) ----
def make_pair_slug(teacher_id: int, student_id: int) -> str:
    return f"teacher:{teacher_id}__student:{student_id}"

@router.post("/chat/room", response_model=ChatRoomOut)
async def teacher_student_room(student_id: int, db: AsyncSession = Depends(get_db), teacher: Teacher = Depends(get_current_teacher)):
    slug = make_pair_slug(teacher.id, student_id)
    exist = await db.execute(select(ChatRoom).where(ChatRoom.slug == slug))
    room = exist.scalar_one_or_none()
    if not room:
        room = ChatRoom(slug=slug, is_group=False)
        db.add(room)
        await db.commit()
    return ChatRoomOut(slug=slug)

@router.get("/chat/history", response_model=list[ChatMessageOut])
async def chat_history(student_id: int, limit: int = 50, before_id: int | None = None,
                       db: AsyncSession = Depends(get_db), teacher: Teacher = Depends(get_current_teacher)):
    slug = make_pair_slug(teacher.id, student_id)
    q = select(ChatMessage).where(ChatMessage.room_slug == slug)
    if before_id:
        q = q.where(ChatMessage.id < before_id)
    q = q.order_by(ChatMessage.id.desc()).limit(limit)
    res = await db.execute(q)
    rows = list(reversed(res.scalars().all()))
    return [
        ChatMessageOut.model_validate(r) for r in rows
    ]
