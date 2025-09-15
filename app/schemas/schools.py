# app/schemas/schools.py
from pydantic import BaseModel, ConfigDict
from typing import Optional

class SchoolBase(BaseModel):
    name: str
    address: Optional[str] = None

class SchoolCreate(SchoolBase):
    pass

class SchoolUpdate(BaseModel):
    name: Optional[str] = None
    address: Optional[str] = None

class SchoolOut(SchoolBase):
    id: int

    class Config:
        model_config = ConfigDict(from_attributes=True)
