from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.models.score import Score
from app.schemas.score import ScoreCreate
from datetime import date

async def create_score(db: AsyncSession, data: ScoreCreate):
    new_score = Score(**data.dict())
    db.add(new_score)
    await db.commit()
    await db.refresh(new_score)
    return new_score

async def get_scores_by_student(db: AsyncSession, student_id: int, start_date: date, end_date: date):
    result = await db.execute(
        select(Score).where(
            Score.student_id == student_id,
            Score.date >= start_date,
            Score.date <= end_date
        )
    )
    return result.scalars().all()

async def get_score_by_id(db: AsyncSession, score_id: int):
    result = await db.execute(select(Score).where(Score.id == score_id))
    return result.scalar_one_or_none()

async def get_student_scores(db: AsyncSession, student_id: int, start_date=None, end_date=None):
    stmt = select(Score).where(Score.student_id == student_id)
    if start_date:
        stmt = stmt.where(Score.date >= start_date)
    if end_date:
        stmt = stmt.where(Score.date <= end_date)
    result = await db.execute(stmt)
    return result.scalars().all()