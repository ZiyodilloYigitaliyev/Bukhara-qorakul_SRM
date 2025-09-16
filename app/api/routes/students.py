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
from sqlalchemy import or_, select
from app.models.student import Student
from app.models.schools import School
from fastapi import APIRouter, Depends, HTTPException, Query





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


@router.get("/{school_id}/students", response_model=list[StudentOut])
async def get_students_by_school(
    school_id: int,
    db: AsyncSession = Depends(get_db),
    user=Depends(require_role("staff", "superuser")),
    # ixtiyoriy filtr va paginatsiya
    search: str | None = Query(None, description="Ism/familiya bo‘yicha qidiruv"),
    class_name: str | None = Query(None, description="Masalan: 5A"),
    is_active: bool | None = Query(None, description="True/False"),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
):
    # 1) Maktab mavjudligini tekshiramiz (404 bermasa, frontendga aniq xabar)
    res_school = await db.execute(select(School).where(School.id == school_id))
    school = res_school.scalar_one_or_none()
    if not school:
        raise HTTPException(status_code=404, detail="Maktab topilmadi")

    # 2) Asosiy so'rov
    q = select(Student).where(Student.school_id == school_id)

    if is_active is not None:
        q = q.where(Student.is_active.is_(is_active))

    if class_name:
        q = q.where(Student.class_name == class_name)

    if search:
        s = f"%{search.strip()}%"
        # Eng xavfsiz maydonlar: first_name & last_name (agar login/phone bo'lsa, qo‘shib ketish mumkin)
        q = q.where(
            or_(
                Student.first_name.ilike(s),
                Student.last_name.ilike(s),
            )
        )

    q = q.order_by(Student.last_name.asc(), Student.first_name.asc()).offset(offset).limit(limit)

    result = await db.execute(q)
    students = result.scalars().all()
    return students




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