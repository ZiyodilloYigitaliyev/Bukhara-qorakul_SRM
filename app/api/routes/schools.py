from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.db.database import get_db
from app.models.schools import School
from app.schemas.schools import SchoolCreate, SchoolOut, SchoolUpdate
from app.core.dependencies import require_role
from app.schemas.student import StudentOut
router = APIRouter(
    prefix="/schools",
    tags=["Schools"]
)


@router.post("/", response_model=SchoolOut)
async def create_school(
    data: SchoolCreate,
    db: AsyncSession = Depends(get_db),
    user=Depends(require_role("superuser"))
):
    new_school = School(**data.dict())
    db.add(new_school)
    await db.commit()
    await db.refresh(new_school)
    return new_school


@router.get("/", response_model=list[SchoolOut])
async def get_schools(
    db: AsyncSession = Depends(get_db),
    user=Depends(require_role("staff", "superuser"))
):
    result = await db.execute(select(School))
    return result.scalars().all()


@router.get("/{school_id}", response_model=SchoolOut)
async def get_school(
    school_id: int,
    db: AsyncSession = Depends(get_db),
    user=Depends(require_role("staff", "superuser"))
):
    result = await db.execute(select(School).where(School.id == school_id))
    school = result.scalar_one_or_none()
    if not school:
        raise HTTPException(status_code=404, detail="Maktab topilmadi")
    return school


@router.put("/{school_id}", response_model=SchoolOut)
async def update_school(
    school_id: int,
    data: SchoolUpdate,
    db: AsyncSession = Depends(get_db),
    user=Depends(require_role("superuser"))
):
    result = await db.execute(select(School).where(School.id == school_id))
    school = result.scalar_one_or_none()
    if not school:
        raise HTTPException(status_code=404, detail="Maktab topilmadi")

    for key, value in data.dict(exclude_unset=True).items():
        setattr(school, key, value)

    await db.commit()
    await db.refresh(school)
    return school


@router.delete("/{school_id}")
async def delete_school(
    school_id: int,
    db: AsyncSession = Depends(get_db),
    user=Depends(require_role("superuser"))
):
    result = await db.execute(select(School).where(School.id == school_id))
    school = result.scalar_one_or_none()
    if not school:
        raise HTTPException(status_code=404, detail="Maktab topilmadi")

    await db.delete(school)
    await db.commit()
    return {"detail": "Maktab muvaffaqiyatli o'chirildi"}
