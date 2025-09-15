from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from app.db.base import Base

class Subject(Base):
    __tablename__ = "subjects"

    id = Column(Integer, primary_key=True, index=True)
    # majburiy
    name = Column(String(100), nullable=False)          # Masalan: "Matematika"
    color_hex = Column(String(7), nullable=False)       # "#3B82F6"
    is_active = Column(Boolean, nullable=False, default=True)

    # multi-school
    school_id = Column(Integer, ForeignKey("schools.id", ondelete="CASCADE"), nullable=False)
    school = relationship("School", backref="subjects")

    schedules = relationship("Schedule", back_populates="subject")

    __table_args__ = (
        UniqueConstraint("school_id", "name", name="uq_subject_name_per_school"),
    )
