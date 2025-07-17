from pydantic import BaseModel
from datetime import date
from typing import Optional

class StudentBase(BaseModel):
    first_name: str
    last_name: str
    passport_number: Optional[str] = None
    student_code: str
    image_url: Optional[str] = None
    birth_date: Optional[date] = None
    gender: Optional[str] = None

    parent_father_name: Optional[str] = None
    parent_father_phone: Optional[str] = None
    parent_mother_name: Optional[str] = None
    parent_mother_phone: Optional[str] = None

    class_name: Optional[str] = None
    is_active: Optional[bool] = True
    # Avtomatik generatsiya qilinadi
    login: Optional[str] = None  # avtomatik generatsiya qilinadi
    password: Optional[str] = None  # avtomatik generatsiya qilinadi
class StudentCreate(StudentBase):
    pass

class StudentUpdate(StudentBase):
    pass

class StudentOut(BaseModel):
    id: int
    first_name: str
    last_name: str
    student_code: str
    class_name: Optional[str]
    birth_date: date
    gender: str
    is_active: bool
    passport_number: Optional[str] = None
    image_url: Optional[str] = None
    parent_father_name: Optional[str] = None
    parent_father_phone: Optional[str] = None
    parent_mother_name: Optional[str] = None
    parent_mother_phone: Optional[str] = None
     

    class Config:
        from_attributes = True
