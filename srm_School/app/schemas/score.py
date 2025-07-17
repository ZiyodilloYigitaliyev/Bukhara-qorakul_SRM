from pydantic import BaseModel
from datetime import date

class ScoreCreate(BaseModel):
    student_id: int
    subject: str       # <= BU YERDA BO‘LISHI KERAK
    score: float
    date: date
    is_bonus: bool = False

class ScoreOut(BaseModel):
    id: int
    student_id: int
    date: date
    subject: str | None = None  # agar fanni qo‘shgan bo‘lsangiz
    score: float
    is_bonus: bool

    class Config:
        from_attributes = True 

class ScoreUpdate(BaseModel):
    score: float | None = None  # 0.0 ~ 4.5
    is_bonus: bool | None = None

    class Config:
        from_attributes = True 