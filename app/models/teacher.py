from sqlalchemy import Column, ForeignKey, Integer, String, Boolean, UniqueConstraint
from app.db.base import Base
from sqlalchemy.orm import relationship


class Teacher(Base):
    __tablename__ = "teachers"

    id = Column(Integer, primary_key=True, index=True)
    first_name = Column(String, nullable=False)
    last_name = Column(String, nullable=False)
    subject = Column(String, nullable=False)
    phone_number = Column(String, unique=True, nullable=False)
     # Face terminal bilan bog‘lash
    face_terminal_id = Column(Integer, unique=True, nullable=True)
    login = Column(String(50), unique=True, nullable=False)
    hashed_password = Column(String(128), nullable=False)
    is_active = Column(Boolean, default=True)
    schedules = relationship("Schedule", back_populates="teacher")
    school_id = Column(Integer, ForeignKey("schools.id"), nullable=False)
    school = relationship("School", backref="teachers")
    # Attendance’ga bog‘lanish
    attendances = relationship("Attendance", back_populates="teacher", cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint("face_terminal_id", name="uq_teacher_face_terminal_id"),
    )