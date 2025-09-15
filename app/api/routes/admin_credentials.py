# app/api/routes/admin_credentials.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.core.dependencies import get_current_user  # umumiy user dep (superuser/staff tekshirish uchun)
from app.schemas.credentials import ResetCredentialsIn, ResetCredentialsOut
from app.crud.teacher import reset_teacher_credentials
from app.crud.student import reset_student_credentials

router = APIRouter(prefix="/admin/BQS/@dmin", tags=["Admin - Credentials"])

def _assert_admin(user):
    # loyihangizdagi rollar bo‘yicha moslang
    # masalan: ("superuser", "staff")
    if getattr(user, "role", None) not in ("superuser", "staff"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Ruxsat yo‘q")

@router.post("/teachers/{teacher_id}/reset-credentials", response_model=ResetCredentialsOut)
async def admin_reset_teacher_credentials(
    teacher_id: int,
    body: ResetCredentialsIn,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    _assert_admin(user)
    teacher, temp_password = await reset_teacher_credentials(db, teacher_id, regenerate_login=body.regenerate_login)
    return ResetCredentialsOut(
        id=teacher.id,
        role="teacher",
        login=teacher.login,
        temp_password=temp_password,
    )

@router.post("/students/{student_id}/reset-credentials", response_model=ResetCredentialsOut)
async def admin_reset_student_credentials(
    student_id: int,
    body: ResetCredentialsIn,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    _assert_admin(user)
    student, temp_password = await reset_student_credentials(db, student_id, regenerate_login=body.regenerate_login)
    return ResetCredentialsOut(
        id=student.id,
        role="student",
        login=student.login,
        temp_password=temp_password,
    )
