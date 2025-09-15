from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.database import get_db
from app.schemas.teacher import TeacherLogin, TokenResponse, TeacherOut
from app.services.teacher_service import get_teacher_by_login
from app.core.security import verify_password, create_access_token

router = APIRouter(tags=["Auth - Teacher"])

@router.post("/login/teacher", response_model=TokenResponse)
async def login_teacher(data: TeacherLogin, db: AsyncSession = Depends(get_db)):
    teacher = await get_teacher_by_login(db, data.login)
    if not teacher or not verify_password(data.password, teacher.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Login yoki parol noto‘g‘ri")

    token_payload = {
        "sub": str(teacher.id),
        "role": "teacher",
        "login": teacher.login,
        "school_id": teacher.school_id,
    }
    access_token, expires_at = create_access_token(token_payload)

    return {
        "access_token": access_token,
        # Yuqoridagi qator shart emas. Quyida sodda variant:
        "expires_in": 60 * 24 * 30,  # agar settingsdan aniq qiymat qaytarmoqchi bo‘lsangiz, settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60 qiling
        "expires_at": expires_at,
        "role": "teacher",
        "teacher": TeacherOut.model_validate(teacher),
        "token_type": "bearer",
    }
