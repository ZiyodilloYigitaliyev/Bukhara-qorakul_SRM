# app/schemas/teacher.py
from pydantic import BaseModel, ConfigDict
from typing import Optional, Literal
from datetime import datetime

# ---- Out (read) ----
class TeacherOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    first_name: str
    last_name: str
    subject: str
    phone_number: str
    face_terminal_id: Optional[int] = None
    login: str
    is_active: bool
    school_id: int

# ---- Create/Update (write) ----
class TeacherCreate(BaseModel):
    first_name: str
    last_name: str
    subject: str
    phone_number: str
    face_terminal_id: Optional[int] = None
    is_active: bool = True
    school_id: int

# Routeringiz "CreateTeacher" nomini kutayotgan ekan — moslik uchun alias
CreateTeacher = TeacherCreate

class TeacherUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    subject: Optional[str] = None
    phone_number: Optional[str] = None
    login: Optional[str] = None
    password: Optional[str] = None          # agar yuborilsa, hash qilib yangilang
    face_terminal_id: Optional[int] = None
    is_active: Optional[bool] = None

# ---- Auth uchun ----
class TeacherLogin(BaseModel):
    login: str
    password: str
    
class TeacherCreateResponse(BaseModel):
    teacher: TeacherOut
    temp_password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: Literal["bearer"] = "bearer"
    expires_in: int
    expires_at: datetime
    role: Literal["teacher"] = "teacher"
    teacher: TeacherOut
