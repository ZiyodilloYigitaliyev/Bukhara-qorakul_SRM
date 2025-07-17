from pydantic import BaseModel, EmailStr
from typing import Optional

class CreateTeacher(BaseModel):
    first_name: str
    last_name: str
    phone_number: str
    subject: str

class TeacherOut(CreateTeacher):
    id: int
    first_name: str
    last_name: str
    phone_number: str
    subject: str

    class Config:
        orm_mode = True
