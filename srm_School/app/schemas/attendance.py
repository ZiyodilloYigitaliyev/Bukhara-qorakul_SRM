# app/schemas/attendance.py
from datetime import date, time, datetime
from pydantic import BaseModel
from typing import Optional


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

class TerminalLog(BaseModel):
    serial_number: str  # Qurilma serial raqami
    datetime: datetime  # Log vaqti
    event_type: int     # Asosiy event turi
    sub_event_type: int # Sub event turi
    user_type: str      # Foydalanuvchi turi
    employee_id: int    # Student ID (terminaldan kelgan)
    device_name: str    # Qurilma nomi

