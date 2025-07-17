from sqlalchemy import Column, Integer, String, Enum, Boolean
from app.db.base import Base
import enum

class UserRole(str, enum.Enum):
    student = "student"
    teacher = "teacher"
    staff = "staff"
    superuser = "superuser"

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    full_name = Column(String, nullable=False)
    username = Column(String, unique=True, index=True)
    hashed_password = Column(String, nullable=False)
    role = Column(Enum(UserRole), default=UserRole.student)
    is_active = Column(Boolean, default=True)
