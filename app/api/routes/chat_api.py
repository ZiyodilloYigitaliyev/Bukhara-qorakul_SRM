from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, insert
from typing import Optional, List
from app.db.database import get_db
from app.models.chat import ChatRoom, ChatMessage

router = APIRouter(prefix="/chat", tags=["Chat"])

def make_pair_slug(teacher_id: int, student_id: int) -> str:
    return f"teacher:{teacher_id}__student:{student_id}"

@router.post("/room")
async def get_or_create_room(teacher_id: int, student_id: int, db: AsyncSession = Depends(get_db)):
    slug = make_pair_slug(teacher_id, student_id)
    res = await db.execute(select(ChatRoom).where(ChatRoom.slug == slug))
    room = res.scalar_one_or_none()
    if not room:
        await db.execute(insert(ChatRoom).values(slug=slug, is_group=False))
        await db.commit()
    return {"slug": slug}

@router.get("/history")
async def history(room_slug: str, limit: int = 50, before_id: Optional[int] = None, db: AsyncSession = Depends(get_db)):
    q = select(ChatMessage).where(ChatMessage.room_slug == room_slug)
    if before_id:
        q = q.where(ChatMessage.id < before_id)
    q = q.order_by(ChatMessage.id.desc()).limit(limit)
    res = await db.execute(q)
    rows = list(reversed(res.scalars().all()))
    return [ {
        "id": r.id,
        "room_slug": r.room_slug,
        "sender_role": r.sender_role,
        "sender_id": r.sender_id,
        "message_type": r.message_type,
        "text": r.text,
        "delivered": r.delivered,
        "read_at": r.read_at,
        "created_at": r.created_at
    } for r in rows ]
