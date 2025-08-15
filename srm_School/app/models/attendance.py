from sqlalchemy import Column, Integer, Boolean, Date, String, Time, ForeignKey
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

    # YANGI MAYDONLAR
    event_type = Column(Integer, nullable=True)
    sub_event_type = Column(Integer, nullable=True)
    user_type = Column(String, nullable=True)
    serial_no = Column(String, nullable=True)
    device_name = Column(String, nullable=True)
    status = Column(String, nullable=True)  

    student = relationship("Student", back_populates="attendances")
    school_id = Column(Integer, ForeignKey("schools.id"), nullable=False)
    school = relationship("School", backref="attendance")
