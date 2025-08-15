from pydantic import BaseModel, ConfigDict
from datetime import date
from typing import Optional

class StudentBase(BaseModel):
    first_name: str
    last_name: str
    passport_number: Optional[str] 
    student_code: str
    image_url: Optional[str]
    birth_date: Optional[date]
    gender: Optional[str]
    # Optional field for face terminal ID
    face_terminal_id: Optional[int]  # This can be used for facial recognition systems
    # Optional fields for parent information
    parent_father_name: Optional[str]
    parent_father_phone: Optional[str]
    parent_mother_name: Optional[str]
    parent_mother_phone: Optional[str]

    class_name: Optional[str] 
    is_active: Optional[bool]
    login: Optional[str] = None
    password: Optional[str] = None
    school_id: int

class StudentCreate(StudentBase):
    pass

class StudentUpdate(StudentBase):
    pass

class StudentOut(BaseModel):
    id: int
    first_name: str
    last_name: str
    passport_number: Optional[str]
    student_code: str
    image_url: Optional[str]
    birth_date: Optional[date]  
    gender: Optional[str] 
    face_terminal_id: Optional[int]
    # Parent information
    parent_father_name: Optional[str]
    parent_father_phone: Optional[str]
    parent_mother_name: Optional[str]
    parent_mother_phone: Optional[str]
    class_name: Optional[str]
    is_active: bool
    login: str
    # School info
    school_id: int
    school_name: str
    school_address: Optional[str]

    model_config = ConfigDict(from_attributes=True)
    
    @classmethod
    def model_validate(cls, student):
        return cls(
            id=student.id,
            first_name=student.first_name,
            last_name=student.last_name,
            passport_number=student.passport_number,
            student_code=student.student_code,
            image_url=student.image_url,
            birth_date=student.birth_date,
            gender=student.gender,
            face_terminal_id=student.face_terminal_id,
            parent_father_name=student.parent_father_name,
            parent_father_phone=student.parent_father_phone,
            parent_mother_name=student.parent_mother_name,
            parent_mother_phone=student.parent_mother_phone,
            class_name=student.class_name,
            is_active=student.is_active,
            login=student.login,
            school_id=student.school_id,
            school_name=student.school.name if student.school else "",
            school_address=student.school.address if student.school else None,
        )

class StudentOutWithPassword(BaseModel):
    student: StudentOut
    password: str