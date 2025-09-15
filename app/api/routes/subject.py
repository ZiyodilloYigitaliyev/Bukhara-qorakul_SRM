from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from typing import List

from app.db.database import get_db
from app.core.dependencies import get_current_user
from app.models.subject import Subject
from app.schemas.subject import SubjectCreate, SubjectUpdate, SubjectOut

router = APIRouter(prefix="/subjects", tags=["Subjects"])

def _require_staff_or_admin(user=Depends(get_current_user)):
    if getattr(user, "role", None) not in ("staff", "admin", "superuser"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Ruxsat yo‘q")
    return user

@router.post("/", response_model=SubjectOut, dependencies=[Depends(_require_staff_or_admin)])
async def create_subject(data: SubjectCreate, db: AsyncSession = Depends(get_db)):
    obj = Subject(**data.model_dump())
    db.add(obj)
    try:
        await db.commit()
        await db.refresh(obj)
        return obj
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=409, detail="Bu maktabda shu nomdagi subject allaqachon mavjud")

@router.get("/", response_model=List[SubjectOut], dependencies=[Depends(_require_staff_or_admin)])
async def list_subjects(school_id: int, db: AsyncSession = Depends(get_db)):
    res = await db.execute(
        select(Subject).where(Subject.school_id == school_id).order_by(Subject.name)
    )
    return res.scalars().all()

@router.get("/{subject_id}", response_model=SubjectOut, dependencies=[Depends(_require_staff_or_admin)])
async def get_subject(subject_id: int, db: AsyncSession = Depends(get_db)):
    obj = await db.get(Subject, subject_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Subject topilmadi")
    return obj

@router.patch("/{subject_id}", response_model=SubjectOut, dependencies=[Depends(_require_staff_or_admin)])
async def update_subject(subject_id: int, data: SubjectUpdate, db: AsyncSession = Depends(get_db)):
    obj = await db.get(Subject, subject_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Subject topilmadi")

    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(obj, k, v)

    try:
        await db.commit()
        await db.refresh(obj)
        return obj
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=409, detail="Nom takrorlanmoqda")
