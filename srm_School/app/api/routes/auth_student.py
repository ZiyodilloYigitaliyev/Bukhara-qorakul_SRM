from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi.security import OAuth2PasswordRequestForm

from app.db.database import get_db
from app.schemas.student_auth import LoginSchema, TokenSchema
from app.core.security import create_access_token
from app.core.utils import verify_password
from app.crud.student import get_student_by_login

router = APIRouter()

@router.post("/student-login", response_model=TokenSchema)
async def student_login(data: LoginSchema, db: AsyncSession = Depends(get_db)):
    student = await get_student_by_login(db, data.login)
    if not student or not verify_password(data.password, student.password):
        raise HTTPException(status_code=401, detail="Login yoki parol noto‘g‘ri")

    access_token = create_access_token({"sub": student.login, "role": "student"})
    return {"access_token": access_token, "token_type": "bearer"}
