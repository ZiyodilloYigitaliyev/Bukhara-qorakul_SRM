from pydantic import BaseModel, ConfigDict
from typing import Optional

class ClassCreate(BaseModel):
    name: str
    school_id: int

class ClassUpdate(BaseModel):
    name: Optional[str] = None

class ClassOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    school_id: int
