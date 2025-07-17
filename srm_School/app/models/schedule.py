from sqlalchemy import Column, Integer, ForeignKey, String, Time, Date
from sqlalchemy.orm import relationship
from app.db.base import Base

class Schedule(Base):
    __tablename__ = "schedules"

    id = Column(Integer, primary_key=True, index=True)
    subject = Column(String, nullable=False)
    class_name = Column(String, nullable=False)  # Misol: "1A", "2B"
    day = Column(String, nullable=False)  # Misol: "Monday", "Tuesday"
    start_time = Column(Time, nullable=False)
    end_time = Column(Time, nullable=False)
    teacher_id = Column(Integer, ForeignKey("teachers.id"))
    teacher = relationship("Teacher", back_populates="schedules", lazy="joined") 
