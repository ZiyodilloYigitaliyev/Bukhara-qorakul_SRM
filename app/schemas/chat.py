# app/schemas/chat.py
from __future__ import annotations
from pydantic import BaseModel, ConfigDict
from datetime import datetime
from enum import Enum

class SenderType(str, Enum):
    student = "student"
    teacher = "teacher"

# Minimal “brief” obyektlar (bular StudentOut/TeacherOut bo'lmasa ham ishlaydi)
class StudentBrief(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    first_name: str
    last_name: str
    image_url: str | None = None
    class_name: str | None = None

class TeacherBrief(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    first_name: str
    last_name: str
    image_url: str | None = None

class ChatRoomOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    student: StudentBrief
    teacher: TeacherBrief
    last_message_text: str | None = None
    last_message_at: datetime | None = None
    student_unread: int
    teacher_unread: int
    created_at: datetime

class ChatRoomCreate(BaseModel):
    student_id: int
    teacher_id: int

class ChatMessageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    room_id: int
    sender_type: SenderType
    sender_id: int
    text: str
    is_read: bool
    created_at: datetime

class ChatMessageCreate(BaseModel):
    text: str
