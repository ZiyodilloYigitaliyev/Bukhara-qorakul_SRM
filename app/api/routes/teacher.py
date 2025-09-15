from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.teacher import CreateTeacher, TeacherCreate, TeacherOut
from app.crud import teacher as crud_teacher
from app.core.dependencies import get_db, require_role
from app.crud.teacher import create_teacher as create_teacher_crud
from app.schemas.teacher import TeacherCreateResponse



router = APIRouter(prefix="/teachers", tags=["Teachers"])

@router.post("/", response_model=TeacherCreateResponse)
async def create_teacher(data: TeacherCreate, db: AsyncSession = Depends(get_db),
    user=Depends(require_role("staff", "superuser"))):
    res = await create_teacher_crud(db, data)
    return {
        "teacher": res["teacher"],
        "temp_password": res["temp_password"],  # admin faqat bir marta ko'radi
    }

@router.get("/", response_model=list[TeacherOut])
async def get_all_teachers(
    db: AsyncSession = Depends(get_db),
    user=Depends(require_role("staff", "superuser"))
):
    return await crud_teacher.get_all_teachers(db)

@router.get("/{teacher_id}", response_model=TeacherOut)
async def get_teacher_by_id(
    teacher_id: int,
    db: AsyncSession = Depends(get_db),
    user=Depends(require_role("staff", "superuser"))
):
    teacher = await crud_teacher.get_teacher_by_id(db, teacher_id)
    if not teacher:
        raise HTTPException(status_code=404, detail="O‘qituvchi topilmadi")
    return teacher
