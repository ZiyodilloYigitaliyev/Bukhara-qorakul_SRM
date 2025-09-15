# app/models/chat.py
from __future__ import annotations
from datetime import datetime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import Integer, Text, DateTime, Enum, ForeignKey, UniqueConstraint, Index, func
from app.db.base import Base  # sizdagi Base (declarative_base) qayerda bo'lsa, shuni import qiling
import enum

class SenderType(str, enum.Enum):
    student = "student"
    teacher = "teacher"

class ChatRoom(Base):
    __tablename__ = "chat_rooms"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id", ondelete="CASCADE"), index=True)
    teacher_id: Mapped[int] = mapped_column(ForeignKey("teachers.id", ondelete="CASCADE"), index=True)

    last_message_text: Mapped[str | None] = mapped_column(Text, default=None)
    last_message_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)

    student_unread: Mapped[int] = mapped_column(Integer, default=0)
    teacher_unread: Mapped[int] = mapped_column(Integer, default=0)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    student = relationship("Student")
    teacher = relationship("Teacher")
    messages = relationship("ChatMessage", back_populates="room", cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint("student_id", "teacher_id", name="uq_chat_room_student_teacher"),
        Index("ix_chat_room_pair", "student_id", "teacher_id"),
    )

class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    room_id: Mapped[int] = mapped_column(ForeignKey("chat_rooms.id", ondelete="CASCADE"), index=True)

    sender_type: Mapped[SenderType] = mapped_column(Enum(SenderType), index=True)
    sender_id: Mapped[int] = mapped_column(Integer, index=True)
    text: Mapped[str] = mapped_column(Text)

    is_read: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)

    room = relationship("ChatRoom", back_populates="messages")

    __table_args__ = (
        Index("ix_chat_messages_room_created", "room_id", "created_at"),
    )
