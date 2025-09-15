from sqlalchemy import Column, Integer, ForeignKey, Time, String, UniqueConstraint
from sqlalchemy.orm import relationship
from app.db.base import Base

class Schedule(Base):
    __tablename__ = "schedules"

    id = Column(Integer, primary_key=True)
    school_id = Column(Integer, ForeignKey("schools.id"), nullable=False)

    day_of_week = Column(Integer, nullable=False)   # 1=Mon ... 7=Sun
    start_time  = Column(Time, nullable=False)
    end_time    = Column(Time, nullable=False)

    subject_id  = Column(Integer, ForeignKey("subjects.id"), nullable=False)
    subject     = relationship("Subject", back_populates="schedules", lazy="joined")

    teacher_id  = Column(Integer, ForeignKey("teachers.id"), nullable=False)
    teacher     = relationship("Teacher", back_populates="schedules", lazy="joined")

    class_id  = Column(Integer, ForeignKey("classes.id"), nullable=True)
    clasname  = relationship("ClassName", back_populates="schedules", lazy="joined")

    student_id  = Column(Integer, ForeignKey("students.id"), nullable=True)  # 1-1/elektiv
    student     = relationship("Student", lazy="joined")

    # Bir vaqt oralig‘ida aynan shu target (class_id/student_id) va teacher uchun dars takrorlanmasin
    __table_args__ = (
        UniqueConstraint("school_id","day_of_week","start_time","end_time","teacher_id","class_id","student_id",
                         name="uq_schedule_slot"),
    )
