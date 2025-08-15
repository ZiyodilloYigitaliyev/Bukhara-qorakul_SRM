from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.db.database import get_db
from app.models.device import Device
from app.schemas.device import DeviceCreate, DeviceUpdate, DeviceOut
from app.core.dependencies import require_role

router = APIRouter(prefix="/devices", tags=["Devices"])

@router.post("/", response_model=DeviceOut)
async def create_device(
    data: DeviceCreate,
    db: AsyncSession = Depends(get_db),
    user=Depends(require_role("superuser"))
):
    existing = await db.execute(select(Device).where(Device.serial_number == data.serial_number))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Bu serial number bilan qurilma allaqachon mavjud")

    device = Device(**data.dict())
    db.add(device)
    await db.commit()
    await db.refresh(device)
    return device


@router.get("/", response_model=list[DeviceOut])
async def get_all_devices(
    db: AsyncSession = Depends(get_db),
    user=Depends(require_role("staff", "superuser"))
):
    result = await db.execute(select(Device))
    return result.scalars().all()


@router.get("/{device_id}", response_model=DeviceOut)
async def get_device(
    device_id: int,
    db: AsyncSession = Depends(get_db),
    user=Depends(require_role("staff", "superuser"))
):
    result = await db.execute(select(Device).where(Device.id == device_id))
    device = result.scalar_one_or_none()
    if not device:
        raise HTTPException(status_code=404, detail="Qurilma topilmadi")
    return device


@router.put("/{device_id}", response_model=DeviceOut)
async def update_device(
    device_id: int,
    data: DeviceUpdate,
    db: AsyncSession = Depends(get_db),
    user=Depends(require_role("superuser"))
):
    result = await db.execute(select(Device).where(Device.id == device_id))
    device = result.scalar_one_or_none()
    if not device:
        raise HTTPException(status_code=404, detail="Qurilma topilmadi")

    for key, value in data.dict(exclude_unset=True).items():
        setattr(device, key, value)

    await db.commit()
    await db.refresh(device)
    return device


@router.delete("/{device_id}")
async def delete_device(
    device_id: int,
    db: AsyncSession = Depends(get_db),
    user=Depends(require_role("superuser"))
):
    result = await db.execute(select(Device).where(Device.id == device_id))
    device = result.scalar_one_or_none()
    if not device:
        raise HTTPException(status_code=404, detail="Qurilma topilmadi")

    await db.delete(device)
    await db.commit()
    return {"detail": "Qurilma o‘chirildi"}
