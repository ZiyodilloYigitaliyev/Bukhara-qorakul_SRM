from pydantic import BaseModel
from enum import Enum

class UserRole(str, Enum):
    student = "student"
    teacher = "teacher"
    staff = "staff"
    superuser = "superuser"

class UserCreate(BaseModel):
    full_name: str
    username: str
    password: str
    role: UserRole = UserRole.student

class UserOut(BaseModel):
    id: int
    full_name: str
    username: str
    role: UserRole

    class Config:
        from_attributes = True
