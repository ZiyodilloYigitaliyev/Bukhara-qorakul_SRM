from sqlalchemy import Column, Integer, String, DateTime, func
from app.db.base import Base    


class School(Base):
    __tablename__ = "schools"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False)
    address = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Optional: timezone, logo, etc.
