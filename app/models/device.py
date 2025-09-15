from sqlalchemy import Column, ForeignKey, Integer, String
from sqlalchemy.orm import relationship
from app.db.base import Base

class Device(Base):
    __tablename__ = "devices"

    id = Column(Integer, primary_key=True)
    name = Column(String(100), unique=True, nullable=False)  # masalan: "K1T342_Main_Gate"
    serial_number = Column(String(100), unique=True, nullable=False)
    school_id = Column(Integer, ForeignKey("schools.id"), nullable=False)
    school = relationship("School", backref="devices")