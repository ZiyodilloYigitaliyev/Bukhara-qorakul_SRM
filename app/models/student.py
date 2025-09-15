from sqlalchemy import Column, ForeignKey, Integer, String, Date, Boolean
from sqlalchemy.orm import relationship
from app.db.base import Base

class Student(Base):
    __tablename__ = "students"

    id = Column(Integer, primary_key=True, index=True)
    first_name = Column(String(50), nullable=False)
    last_name = Column(String(50), nullable=False)
    passport_number = Column(String(20), unique=True, nullable=True)
    student_code = Column(String(20), unique=True, nullable=False)  # tabel raqam
    image_url = Column(String(255), nullable=True)
    birth_date = Column(Date, nullable=True)
    gender = Column(String(10), nullable=True)
    face_terminal_id = Column(Integer, unique=True, nullable=True)
    add_date = Column(Date, nullable=False)
    address = Column(String(255), nullable=True)

    parent_father_name = Column(String(100), nullable=True)
    parent_father_phone = Column(String(20), nullable=True)
    parent_mother_name = Column(String(100), nullable=True)
    parent_mother_phone = Column(String(20), nullable=True)

    # FK — bitta marta
    class_id = Column(Integer, ForeignKey("classes.id"), nullable=True)

    # RELATIONSHIP nomi 'clasname' (string 'class_name' bilan chalkashmasin)
    clasname = relationship("ClassName", back_populates="students", lazy="joined")

    is_active = Column(Boolean, default=True)
    login = Column(String(50), unique=True, nullable=False)
    hashed_password = Column(String(128), nullable=False)

    # Quyidagilar qarshi modeldagi nom bilan mos bo'lsin:
    attendances = relationship("Attendance", back_populates="student", cascade="all, delete-orphan")
    scores      = relationship("Score",      back_populates="student", cascade="all, delete-orphan")
    payments    = relationship("Payment",    back_populates="student", cascade="all, delete-orphan")

    school_id = Column(Integer, ForeignKey("schools.id"), nullable=False)
    school = relationship("School", backref="students")
