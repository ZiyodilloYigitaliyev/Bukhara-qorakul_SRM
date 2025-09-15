# app/schemas/student.py
from pydantic import BaseModel, Field, field_validator
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

    face_terminal_id: Optional[int] = None
    add_date: Optional[date] = None
    address: Optional[str] = None

    parent_father_name: Optional[str] = None
    parent_father_phone: Optional[str] = None
    parent_mother_name: Optional[str] = None
    parent_mother_phone: Optional[str] = None

    # E'tibor: sizda 'clasname' deb nomlangan maydon ishlatilmoqda
    clasname: Optional[str] = None
    class_id: Optional[int] = None
    is_active: Optional[bool] = True
    school_id: int

    login: Optional[str] = Field(default=None, min_length=3, max_length=64)
    password: Optional[str] = Field(default=None, min_length=6, max_length=128)

    model_config = {"from_attributes": True, "populate_by_name": True}


class StudentCreate(StudentBase):
    pass


class StudentUpdate(StudentBase):
    pass


class StudentOut(BaseModel):
    id: int
    first_name: str
    last_name: str
    student_code: str
    passport_number: Optional[str] = None
    birth_date: Optional[date] = None
    gender: Optional[str] = None
    add_date: Optional[date] = None
    address: Optional[str] = None
    parent_father_name: Optional[str] = None
    parent_father_phone: Optional[str] = None
    parent_mother_name: Optional[str] = None
    parent_mother_phone: Optional[str] = None
    face_terminal_id: Optional[int] = None

    login: str
    image_url: Optional[str] = None
    # ⚠️ ORM'dan relationship obyekt kelishi mumkin, validator pastda stringga aylantiradi
    clasname: Optional[str] = None
    class_id: Optional[int] = None
    is_active: bool
    school_id: int

    model_config = {"from_attributes": True, "populate_by_name": True}

    # --- YANGI: kelayotgan relationship obyektni string/intga aylantirish ---
    @field_validator("clasname", mode="before")
    @classmethod
    def _coerce_clasname(cls, v):
        # string yoki None bo'lsa o'z holicha
        if isinstance(v, (str, type(None))):
            return v
        # relationship obyekt bo'lsa, nomini olishga harakat qilamiz
        # name -> title -> class_name ketma-ketligi bilan:
        return getattr(v, "name", None) or getattr(v, "title", None) or getattr(v, "class_name", None)

    @field_validator("class_id", mode="before")
    @classmethod
    def _coerce_class_id(cls, v):
        if isinstance(v, (int, type(None))):
            return v
        # relationship obyekt bo'lsa id sini olamiz
        return getattr(v, "id", None)


class StudentOutWithPassword(BaseModel):
    student: StudentOut
    password: str
