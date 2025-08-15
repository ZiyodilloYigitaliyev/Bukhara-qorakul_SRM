from sqlalchemy import Column, ForeignKey, Integer, String, Boolean
from app.db.base import Base
from sqlalchemy.orm import relationship


class Teacher(Base):
    __tablename__ = "teachers"

    id = Column(Integer, primary_key=True, index=True)
    first_name = Column(String, nullable=False)
    last_name = Column(String, nullable=False)
    subject = Column(String, nullable=False)
    phone_number = Column(String, unique=True, nullable=False)
    is_active = Column(Boolean, default=True)
    schedules = relationship("Schedule", back_populates="teacher")
    school_id = Column(Integer, ForeignKey("schools.id"), nullable=False)
    school = relationship("School", backref="teachers")