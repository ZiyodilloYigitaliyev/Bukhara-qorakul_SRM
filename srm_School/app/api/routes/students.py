from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.database import get_db
from app.schemas.student import StudentCreate, StudentBase, StudentOut, StudentUpdate, StudentOutWithPassword
from app.crud import student as crud_student
from app.core.dependencies import require_role
from datetime import date
from app.crud.student import get_student_by_id 
from sqlalchemy.orm import joinedload
from datetime import date, timedelta, datetime
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import APIRouter, Depends, HTTPException
from app.crud import crud_student, crud_attendance, crud_score
from app.db.database import get_db
from app.core.dependencies import require_role
from app.schemas.attendance import AttendanceOut
from app.schemas.score import ScoreOut
from fastapi import status
from sqlalchemy import select
from app.models.student import Student

router = APIRouter(prefix="/students", tags=["Students"])

@router.post(
    "/",
    response_model=StudentOutWithPassword,
    status_code=status.HTTP_201_CREATED
)
async def create_student(
    data: StudentCreate,
    db: AsyncSession = Depends(get_db),
    user=Depends(require_role("staff", "superuser"))
):
    return await crud_student.create_student(db, data)

@router.get("/", response_model=list[StudentOut])
async def get_students(
    db: AsyncSession = Depends(get_db),
    user=Depends(require_role("staff", "superuser"))
):
    return await crud_student.get_all_students(db)

@router.get("/{student_id}", response_model=StudentOut)
async def get_student(
    student_id: int,
    db: AsyncSession = Depends(get_db),
    user=Depends(require_role("staff", "superuser"))
):
    student = await crud_student.get_student_by_id(db, student_id)
    if not student:
        raise HTTPException(status_code=404, detail="O'quvchi topilmadi")
    return student

@router.put("/{student_id}", response_model=StudentOut)
async def update_student(
    student_id: int,
    data: StudentUpdate,
    db: AsyncSession = Depends(get_db),
    user=Depends(require_role("staff", "superuser"))
):
    student = await crud_student.update_student(db, student_id, data)
    if not student:
        raise HTTPException(status_code=404, detail="O'quvchi topilmadi")
    return student

@router.delete("/{student_id}")
async def delete_student(
    student_id: int,
    db: AsyncSession = Depends(get_db),
    user=Depends(require_role("superuser"))
):
    success = await crud_student.delete_student(db, student_id)
    if not success:
        raise HTTPException(status_code=404, detail="O'quvchi topilmadi")
    return {"detail": "O'quvchi o'chirildi"}



@router.get("/students/{student_id}/password", response_model=dict)
async def get_student_password_hash(
    student_id: int,
    db: AsyncSession = Depends(get_db),
    user=Depends(require_role("staff", "superuser"))
):
    student = await get_student_by_id(db, student_id)
    if not student:
        raise HTTPException(status_code=404, detail="O‘quvchi topilmadi")
    return {"hashed_password": student.hashed_password}


@router.get("/{student_id}/report")
async def get_student_report(
    student_id: int,
    filter: str = Query(None, description="weekly, monthly, yearly yoki none"),
    db: AsyncSession = Depends(get_db),
    user=Depends(require_role("staff", "superuser"))
):
    # 1. O‘quvchini joinedload bilan olish
    result = await db.execute(
        select(Student).options(joinedload(Student.school)).where(Student.id == student_id)
    )
    student = result.scalar_one_or_none()

    if not student:
        raise HTTPException(status_code=404, detail="O'quvchi topilmadi")

    # 2. Sana diapazonini aniqlash
    today = date.today()
    start_date = None
    end_date = today

    if filter == "weekly":
        start_date = today - timedelta(days=today.weekday())
    elif filter == "monthly":
        start_date = today.replace(day=1)
    elif filter == "yearly":
        start_date = today.replace(month=1, day=1)

    # 3. Davomat va ballarni olish
    attendances = await crud_attendance.get_student_attendance(db, student_id, start_date, end_date)
    scores = await crud_score.get_student_scores(db, student_id, start_date, end_date)

    # 4. StudentOut to‘g‘ri to‘ldirish
    student_dict = {
        **student.__dict__,
        "school_name": student.school.name if student.school else None,
        "school_address": student.school.address if student.school else None,
        "school_created_at": student.school.created_at if student.school else None,
    }

    return {
        "student_id": student_id,
        "filter": filter,
        "student": StudentOut.model_validate(student_dict).model_dump(),
        "attendance": [AttendanceOut.model_validate(a).model_dump() for a in attendances],
        "scores": [ScoreOut.model_validate(s).model_dump() for s in scores],
    }