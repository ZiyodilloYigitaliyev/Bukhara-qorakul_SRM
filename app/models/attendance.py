from sqlalchemy import (
    Column, Integer, Date, Time, Boolean, String,
    ForeignKey, DateTime, Index
)
from sqlalchemy.orm import relationship, synonym
from sqlalchemy.sql import func
from app.db.base import Base


class Attendance(Base):
    __tablename__ = "attendance"

    id = Column(Integer, primary_key=True, index=True)

    # Kim keldi?
    student_id = Column(Integer, ForeignKey("students.id", ondelete="SET NULL"), index=True, nullable=True)
    teacher_id = Column(Integer, ForeignKey("teachers.id", ondelete="SET NULL"), index=True, nullable=True)

    # Sana/vaqt
    date = Column(Date, nullable=False, index=True)
    arrival_time = Column(Time, nullable=True)
    departure_time = Column(Time, nullable=True)

    # Qo‘shimcha ma’lumotlar
    late_minutes = Column(Integer, nullable=True, default=0)
    is_present = Column(Boolean, nullable=True, default=True)
    user_type = Column(String(50), nullable=True)        # "student"/"teacher" va h.k.

    # Yangi: faqat kelish holati ("on_time" yoki "late")
    arrival_status = Column(String(20), nullable=True)

    # Mavjud umumiy status (mas: "left")
    status = Column(String(20), nullable=True)

    school_id = Column(Integer, ForeignKey("schools.id"), nullable=True)

    # Audit
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relations
    student = relationship("Student", back_populates="attendances", lazy="joined")
    teacher = relationship("Teacher", back_populates="attendances", lazy="joined")
    school = relationship("School", backref="attendance")

    # Alias: left_time <-> departure_time (DBda alohida ustun Y O ' Q !)
    left_time = synonym("departure_time")

    __table_args__ = (
        Index("ix_attendance_student_date", "student_id", "date"),
        Index("ix_attendance_teacher_date", "teacher_id", "date"),
    )
