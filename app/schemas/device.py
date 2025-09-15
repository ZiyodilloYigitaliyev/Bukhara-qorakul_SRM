from pydantic import BaseModel
from typing import Optional

class DeviceBase(BaseModel):
    name: str
    serial_number: str
    
    school_id: int

class DeviceCreate(DeviceBase):
    pass

class DeviceUpdate(BaseModel):
    name: Optional[str] = None
    serial_number: Optional[str] = None
    school_id: Optional[int] = None

class DeviceOut(DeviceBase):
    id: int

    class Config:
        from_attributes = True
