from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from fastapi import HTTPException
from typing import List, Optional
from app.models.classroom import ClassName
from app.schemas.classroom import ClassCreate, ClassUpdate

async def create_class(db: AsyncSession, data: ClassCreate) -> ClassName:
    obj = ClassName(**data.model_dump())
    db.add(obj)
    try:
        await db.commit()
        await db.refresh(obj)
        return obj
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=409, detail="Bu maktabda bu class nomi allaqachon mavjud")

async def list_classes(db: AsyncSession, school_id: int) -> List[ClassName]:
    res = await db.execute(
        select(ClassName).where(ClassName.school_id == school_id).order_by(ClassName.name)
    )
    return res.scalars().all()

async def get_class(db: AsyncSession, class_id: int) -> Optional[ClassName]:
    return await db.get(ClassName, class_id)

async def update_class(db: AsyncSession, class_id: int, data: ClassUpdate) -> ClassName:
    obj = await db.get(ClassName, class_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Class topilmadi")
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(obj, k, v)
    try:
        await db.commit()
        await db.refresh(obj)
        return obj
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=409, detail="Nom takrorlanmoqda")

async def delete_class(db: AsyncSession, class_id: int) -> None:
    obj = await db.get(ClassName, class_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Class topilmadi")
    await db.delete(obj)
    await db.commit()
