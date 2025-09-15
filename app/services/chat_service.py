# app/services/chat_service.py
from __future__ import annotations
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, and_, desc
from app.models.chat import ChatRoom, ChatMessage, SenderType
from datetime import datetime, timezone

async def get_or_create_room(db: AsyncSession, student_id: int, teacher_id: int) -> ChatRoom:
    q = await db.execute(
        select(ChatRoom).where(
            ChatRoom.student_id == student_id,
            ChatRoom.teacher_id == teacher_id,
        )
    )
    room = q.scalar_one_or_none()
    if room:
        return room
    room = ChatRoom(student_id=student_id, teacher_id=teacher_id)
    db.add(room)
    await db.flush()
    return room

async def list_rooms_for_student(db: AsyncSession, student_id: int) -> list[ChatRoom]:
    q = await db.execute(
        select(ChatRoom)
        .where(ChatRoom.student_id == student_id)
        .order_by(desc(ChatRoom.last_message_at.nullslast()))
    )
    return list(q.scalars().all())

async def list_rooms_for_teacher(db: AsyncSession, teacher_id: int) -> list[ChatRoom]:
    q = await db.execute(
        select(ChatRoom)
        .where(ChatRoom.teacher_id == teacher_id)
        .order_by(desc(ChatRoom.last_message_at.nullslast()))
    )
    return list(q.scalars().all())

async def list_messages(db: AsyncSession, room_id: int, limit: int = 50, before_id: int | None = None) -> list[ChatMessage]:
    stmt = select(ChatMessage).where(ChatMessage.room_id == room_id)
    if before_id:
        # oldingi xabarlar uchun simple “id dan kichik” filtri
        stmt = stmt.where(ChatMessage.id < before_id)
    stmt = stmt.order_by(desc(ChatMessage.id)).limit(limit)
    res = await db.execute(stmt)
    items = list(res.scalars().all())
    return list(reversed(items))  # eng eskidan yangiga

async def save_message(
    db: AsyncSession,
    room_id: int,
    sender_type: SenderType,
    sender_id: int,
    text: str,
) -> ChatMessage:
    msg = ChatMessage(
        room_id=room_id,
        sender_type=sender_type,
        sender_id=sender_id,
        text=text,
    )
    db.add(msg)
    # room meta yangilash + unread
    q = await db.execute(select(ChatRoom).where(ChatRoom.id == room_id))
    room = q.scalar_one()
    room.last_message_text = text
    room.last_message_at = datetime.now(timezone.utc)

    if sender_type == SenderType.student:
        room.teacher_unread = (room.teacher_unread or 0) + 1
    else:
        room.student_unread = (room.student_unread or 0) + 1

    await db.flush()
    return msg

async def mark_room_read(db: AsyncSession, room_id: int, reader: SenderType) -> None:
    q = await db.execute(select(ChatRoom).where(ChatRoom.id == room_id))
    room = q.scalar_one_or_none()
    if not room:
        return
    if reader == SenderType.student:
        room.student_unread = 0
    else:
        room.teacher_unread = 0
    await db.flush()
