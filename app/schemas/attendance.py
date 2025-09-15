# app/schemas/attendance.py
from pydantic import BaseModel
from typing import Optional, Literal
from datetime import date
from datetime import datetime, time as dtime
from pydantic import Field, field_validator
    

class AttendanceManualCreate(BaseModel):
    # faqat bittasi to‘lsin
    student_id: Optional[int] = None
    teacher_id: Optional[int] = None

    # qo‘lda kiritish turi
    action: Literal["IN", "OUT", "EXCUSED", "ABSENT"]

    # sana/vaqt: time_str = "HH:MM" (bo‘sh bo‘lsa server vaqti olinadi)
    attendance_date: Optional[date] = None
    time_str: Optional[str] = None

    # IN uchun ixtiyoriy (agar berilsa, shu qiymat ishlatiladi)
    late_override: Optional[int] = None

    # ixtiyoriylar
    school_id: Optional[int] = None
    status: Optional[str] = None  # "left" / "excused" / "absent" va h.k.

def _to_hhmm(v):
    if v is None:
        return None
    if isinstance(v, datetime):
        v = v.time()
    if isinstance(v, dtime):
        return v.strftime("%H:%M")
    # agar allaqachon string bo'lsa
    return str(v)

class AttendanceOut(BaseModel):
    id: int
    student_id: Optional[int] = None
    teacher_id: Optional[int] = None

    # 👇 Modeldagi 'date' ustunini 'attendance_date' nomi bilan chiqazamiz
    attendance_date: date = Field(alias="date")

    # 👇 Front string kutsa — validator bilan time obyektini "HH:MM" ga o'girib beramiz
    arrival_time: Optional[str] = None
    departure_time: Optional[str] = None

    late_minutes: Optional[int] = 0
    is_present: Optional[bool] = True
    user_type: Optional[str] = None
    arrival_status: Optional[str] = None
    status: Optional[str] = None
    school_id: Optional[int] = None

    model_config = {
        "from_attributes": True,
        "populate_by_name": True,   # alias ishlashi uchun muhim!
    }

    @field_validator("arrival_time", "departure_time", mode="before")
    @classmethod
    def _coerce_time(cls, v):
        return _to_hhmm(v)

class AttendanceCreate(BaseModel):
    student_id: int
    date: date
    arrival_time: str  # "HH:MM" format
    departure_time: Optional[str] = None  # "HH:MM" format
    late_minutes: Optional[int] = 0
    is_present: Optional[bool] = True
    user_type: Optional[str] = "student"
    arrival_status: Optional[str] = None
    status: Optional[str] = None
    school_id: Optional[int] = None


    class Config:
        orm_mode = True