from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.schemas.score import ScoreCreate, ScoreOut
from app.crud import score as crud_score
from app.db.database import get_db
from typing import List
from datetime import date

router = APIRouter(prefix="/scores", tags=["Scores"])

@router.post("/", response_model=ScoreOut)
async def create_score(data: ScoreCreate, db: AsyncSession = Depends(get_db)):
    return await crud_score.create_score(db, data)

@router.get("/student/{student_id}", response_model=List[ScoreOut])
async def get_student_scores(student_id: int, start_date: date, end_date: date, db: AsyncSession = Depends(get_db)):
    return await crud_score.get_scores_by_student(db, student_id, start_date, end_date)
