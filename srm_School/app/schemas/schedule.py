from pydantic import BaseModel
from datetime import time
from app.schemas.teacher import TeacherOut

class ScheduleBase(BaseModel):
    subject: str
    class_name: str
    day: str
    start_time: time
    end_time: time

class CreateSchedule(ScheduleBase):
    teacher_id: int

class ScheduleOut(BaseModel):
    id: int
    subject: str
    class_name: str
    day: str
    start_time: time
    end_time: time
    teacher: TeacherOut  # Bu teacher_id emas, to‘liq ma’lumotlar bo‘ladi

    class Config:
        orm_mode = True
