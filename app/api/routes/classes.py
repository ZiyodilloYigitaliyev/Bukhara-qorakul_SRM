from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from app.db.database import get_db
from app.core.dependencies import get_current_user
from app.schemas.classroom import ClassCreate, ClassUpdate, ClassOut
from app.crud import classroom as crud_class

router = APIRouter(prefix="/classes", tags=["Classes"])

def _require_staff(user=Depends(get_current_user)):
    if getattr(user, "role", None) not in ("staff", "admin", "superuser"):
        raise HTTPException(status_code=403, detail="Ruxsat yo‘q")
    return user

@router.post("/", response_model=ClassOut, dependencies=[Depends(_require_staff)])
async def create_classroom(data: ClassCreate, db: AsyncSession = Depends(get_db)):
    return await crud_class.create_class(db, data)

@router.get("/", response_model=List[ClassOut], dependencies=[Depends(_require_staff)])
async def list_classrooms(school_id: int = Query(...), db: AsyncSession = Depends(get_db)):
    return await crud_class.list_classes(db, school_id)

@router.get("/{class_id}", response_model=ClassOut, dependencies=[Depends(_require_staff)])
async def get_classroom(class_id: int, db: AsyncSession = Depends(get_db)):
    obj = await crud_class.get_class(db, class_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Class topilmadi")
    return obj

@router.patch("/{class_id}", response_model=ClassOut, dependencies=[Depends(_require_staff)])
async def update_classroom(class_id: int, data: ClassUpdate, db: AsyncSession = Depends(get_db)):
    return await crud_class.update_class(db, class_id, data)

@router.delete("/{class_id}", dependencies=[Depends(_require_staff)])
async def delete_classroom(class_id: int, db: AsyncSession = Depends(get_db)):
    await crud_class.delete_class(db, class_id)
    return {"ok": True}
