from pydantic import BaseModel
from typing import Literal

class Token(BaseModel):
    access_token: str
    token_type: Literal["bearer"]

class TokenOut(Token):
    role: str

    
class LoginRequest(BaseModel):
    username: str
    password: str
    
class StudentLogin(BaseModel):
    login: str
    password: str


class RegisterStaff(BaseModel):
    full_name: str
    username: str
    password: str
    is_admin: bool = False

class StaffOut(BaseModel):
    id: int
    full_name: str
    username: str
    is_admin: bool

    class Config:
        from_attributes = True
