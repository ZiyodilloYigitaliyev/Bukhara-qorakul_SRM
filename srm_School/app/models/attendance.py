# app/models/attendance.py
from sqlalchemy import Column, Integer, Boolean, Date, Time, ForeignKey
from sqlalchemy.orm import relationship
from app.db.base import Base

class Attendance(Base):
    __tablename__ = "attendance"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("students.id"))
    date = Column(Date)
    arrival_time = Column(Time)  
    late_minutes = Column(Integer, default=0)
    is_present = Column(Boolean, default=True)
    student = relationship("Student", back_populates="attendances")
    