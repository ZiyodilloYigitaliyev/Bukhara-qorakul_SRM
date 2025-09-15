from sqlalchemy import Column, Integer, String, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from app.db.base import Base

class ClassName(Base):
    __tablename__ = "classes"

    id = Column(Integer, primary_key=True)
    name = Column(String(50), nullable=False)  # "1A", "9-B"
    school_id = Column(Integer, ForeignKey("schools.id"), nullable=False)

    # Student va Schedule tomonda 'clasname' bo'ladi
    students  = relationship("Student",  back_populates="clasname")
    schedules = relationship("Schedule", back_populates="clasname")

    __table_args__ = (
        UniqueConstraint("school_id", "name", name="uq_class_name_per_school"),
    )
