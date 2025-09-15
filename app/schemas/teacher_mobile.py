from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, Literal
from datetime import datetime, time

# ---- Login / Token ----
class TeacherLogin(BaseModel):
    login: str
    password: str

class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int

# ---- Profile ----
class TeacherProfileOut(BaseModel):
    id: int
    first_name: str
    last_name: str
    subject: Optional[str] = None
    phone: Optional[str] = None

# ---- Schedule ----
class TeacherScheduleOut(BaseModel):
    class_name: str
    subject: str
    start_time: time
    end_time: time
    room: Optional[str] = None

# ---- Score ----
class TeacherScoreCreate(BaseModel):
    student_id: int
    subject: str
    value: float = Field(ge=0, le=4.5)
    comment: Optional[str] = None
    bonus: bool = False  # yakshanba 2.5 qoidasi uchun

class TeacherScoreOut(BaseModel):
    id: int
    student_id: int
    subject: str
    value: float
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

# ---- Chat ----
class ChatRoomOut(BaseModel):
    slug: str

class ChatMessageOut(BaseModel):
    id: int
    room_slug: str
    sender_role: str
    sender_id: int
    message_type: str
    text: Optional[str]
    delivered: bool
    read_at: Optional[datetime]
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)
