# app/api/routes/score.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.schemas.score import ScoreCreate, ScoreOut
from app.crud import score as crud_score
from app.db.database import get_db
from typing import List
from datetime import date

# umumiy JWT user dep
from app.core.dependencies import get_current_user

router = APIRouter(prefix="/scores", tags=["Scores"])

def _require_staff_or_admin(user=Depends(get_current_user)):
    # rollaringizga moslang: "superuser" ni ham ruxsat beramiz
    if getattr(user, "role", None) not in ("staff", "superuser"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Ruxsat yo‘q")
    return user

@router.post("/", response_model=ScoreOut, dependencies=[Depends(_require_staff_or_admin)])
async def create_score(
    data: ScoreCreate,
    db: AsyncSession = Depends(get_db),
):
    return await crud_score.create_score(db, data)

@router.get("/student/{student_id}", response_model=List[ScoreOut], dependencies=[Depends(_require_staff_or_admin)])
async def get_student_scores(
    student_id: int,
    start_date: date,
    end_date: date,
    db: AsyncSession = Depends(get_db),
):
    return await crud_score.get_scores_by_student(db, student_id, start_date, end_date)
