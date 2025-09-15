from sqlalchemy import Column, Integer, Float, ForeignKey, Date, Boolean, String
from sqlalchemy.orm import relationship
from app.db.base import Base

class Score(Base):
    __tablename__ = "scores"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False)
    subject = Column(String, nullable=False)  # agar fanni qo‘shgan bo‘lsangiz
    score = Column(Float, nullable=False)
    date = Column(Date, nullable=False)
    is_bonus = Column(Boolean, default=False)
    student = relationship("Student", back_populates="scores")
    def to_dict(self):
        return {
            "id": self.id,
            "student_id": self.student_id,
            "subject": self.subject,
            "score": self.score,
            "date": self.date.isoformat(),
            "is_bonus": self.is_bonus,
        }
