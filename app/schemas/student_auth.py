from pydantic import BaseModel

class LoginSchema(BaseModel):
    login: str
    password: str

class TokenSchema(BaseModel):
    access_token: str
    token_type: str
