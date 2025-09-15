# app/core/dependencies.py
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.models.user import User
from app.db.database import get_db
from app.core.config import settings

from app.models.student import Student  # bu sizning student model
from app.schemas.student import StudentOut
from app.services.teacher_service import get_teacher_by_id


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")
oauth2_scheme_teacher = OAuth2PasswordBearer(tokenUrl="/login/teacher")
# oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/login/student")

# Tokenni ochib, userni olish
async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db)
):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid credentials",
    )

    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        sub = payload.get("sub")
        if sub is None:
            raise credentials_exception
        user_id: int = int(sub)
    except (JWTError, ValueError):
        raise credentials_exception

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise credentials_exception

    return user

# Ruxsatlar tekshiruvchi funksiyalar
def require_role(*allowed_roles):
    async def role_checker(user=Depends(get_current_user)):
        if user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to perform this action"
            )
        return user
    return role_checker

async def get_current_student_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db)
):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid student token",
    )

    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        sub = payload.get("sub")
        if sub is None:
            raise credentials_exception
        student_id: int = int(sub)
    except (JWTError, ValueError):
        raise credentials_exception

    result = await db.execute(select(Student).where(Student.id == student_id))
    student = result.scalar_one_or_none()

    if not student:
        raise credentials_exception

    return student  # Bu student obyektini mobile_api.py ga yuboradi

async def get_current_teacher_user(
    token: str = Depends(oauth2_scheme_teacher),
    db: AsyncSession = Depends(get_db),
):
    credentials_exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Tizimga kirish rad etildi (teacher).",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        role: str = payload.get("role")
        sub: str = payload.get("sub")
        if role != "teacher" or sub is None:
            raise credentials_exc
        teacher_id = int(sub)
    except (JWTError, ValueError):
        raise credentials_exc

    teacher = await get_teacher_by_id(db, teacher_id)
    if not teacher or not teacher.is_active:
        raise credentials_exc
    return teacher