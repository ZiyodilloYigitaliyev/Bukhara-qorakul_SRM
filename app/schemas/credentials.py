# app/schemas/credentials.py
from pydantic import BaseModel, ConfigDict
from typing import Literal

class ResetCredentialsIn(BaseModel):
    regenerate_login: bool = False

class ResetCredentialsOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    role: Literal["teacher", "student"]
    login: str
    temp_password: str
