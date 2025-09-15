# app/api/routes/auth_student.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from passlib.context import CryptContext
from app.models.student import Student
from app.schemas.auth import StudentLogin, Token
from app.db.database import get_db
from app.core.security import create_access_token

router = APIRouter(prefix="/login", tags=["Mobile Login"])
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

@router.post("/student", response_model=Token)
async def student_login(data: StudentLogin, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Student).where(Student.login == data.login))
    student = result.scalar_one_or_none()

    if not student:
        raise HTTPException(status_code=401, detail="Login topilmadi")

    if not pwd_context.verify(data.password, student.hashed_password):
        raise HTTPException(status_code=401, detail="Parol noto‘g‘ri")

    access_token = create_access_token({"sub": str(student.id), "role": "student"})
    return {
        "access_token": access_token,
        "token_type": "bearer"  
    }
