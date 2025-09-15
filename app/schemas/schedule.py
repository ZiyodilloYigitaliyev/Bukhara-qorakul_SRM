from pydantic import BaseModel, ConfigDict, field_validator, model_validator
from datetime import time
from typing import Optional
from app.schemas.subject import SubjectOut
from app.schemas.teacher import TeacherOut
from app.schemas.classroom import ClassOut, ClassCreate

class ScheduleCreate(BaseModel):
    school_id: int
    day_of_week: int            # 1..7
    start_time: time
    end_time: time
    subject_id: int
    teacher_id: int
    class_id: Optional[int] = None
    student_id: Optional[int] = None

    @field_validator("day_of_week")
    @classmethod
    def _dow(cls, v):
        if v < 1 or v > 7: raise ValueError("day_of_week 1..7 bo‘lishi kerak")
        return v

    @model_validator(mode="after")
    def _target_required(self):
        if not self.class_id and not self.student_id:
            raise ValueError("class_id yoki student_id dan biri majburiy")
        return self

class ScheduleOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    day_of_week: int
    start_time: time
    end_time: time
    subject: SubjectOut
    teacher: TeacherOut
    classroom: Optional[ClassOut] = None
    student_id: Optional[int] = None
