# app/schemas/attendance.py
from datetime import date, time, datetime
from pydantic import BaseModel
from typing import Optional

class AttendanceCreate(BaseModel):
    student_id: int
    date: date
    check_in_time: time | None = None
    is_present: bool
    late_minutes: int = 0

class AttendanceOut(BaseModel):
    id: int
    student_id: int
    date: date
    arrival_time: Optional[time] = None
    late_minutes: Optional[int] = None
    is_present: bool  # ← bu bor, `status` va `source` yo‘q

    class Config:
        from_attributes = True

class AttendanceCreate(BaseModel):
    student_id: int
    date: date
    arrival_time: datetime
