# app/schemas/subject.py
from pydantic import BaseModel, ConfigDict, field_validator
from typing import Optional
import re

HEX = re.compile(r"^#([0-9A-Fa-f]{6})$")

def _norm_hex(v: Optional[str], required: bool) -> Optional[str]:
    if v is None or v == "":
        if required:
            raise ValueError("color must be #RRGGBB")
        return None
    s = v.strip()
    if not s.startswith("#"):
        s = "#" + s
    if not HEX.match(s):
        raise ValueError("color must be #RRGGBB")
    return s.upper()

class SubjectBase(BaseModel):
    name: str
    color_hex: str
    is_active: bool = True
    school_id: int

    @field_validator("color_hex", mode="before")
    @classmethod
    def _color_hex_ok(cls, v):
        return _norm_hex(v, required=True)

class SubjectCreate(SubjectBase):
    pass

class SubjectUpdate(BaseModel):
    name: Optional[str] = None
    color_hex: Optional[str] = None
    is_active: Optional[bool] = None

    @field_validator("color_hex", mode="before")
    @classmethod
    def _color_hex_ok(cls, v):
        return _norm_hex(v, required=False)

class SubjectOut(SubjectBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
