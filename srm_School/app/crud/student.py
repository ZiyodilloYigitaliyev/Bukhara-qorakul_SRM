from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.models.student import Student
from app.schemas.student import StudentCreate, StudentUpdate
from fastapi import HTTPException
from app.api.routes import auth, students
from app.core.utils import hash_password, generate_random_password


async def create_student(db: AsyncSession, data: StudentCreate):
    if not data.login:
        data.login = f"{data.first_name.lower()}.{data.last_name.lower()}"
    if not data.password:
        raw_password = generate_random_password()
        hashed_password = hash_password(raw_password)
    else:
        raw_password = data.password
        hashed_password = hash_password(data.password)

    new_student = Student(
        first_name=data.first_name,
        last_name=data.last_name,
        login=data.login,
        hashed_password=hashed_password,
        passport_number=data.passport_number,
        student_code=data.student_code,
        image_url=data.image_url,
        birth_date=data.birth_date,
        parent_father_name=data.parent_father_name,
        parent_father_phone=data.parent_father_phone,
        parent_mother_name=data.parent_mother_name,
        parent_mother_phone=data.parent_mother_phone,
        class_name=data.class_name,
        is_active=data.is_active if data.is_active is not None else True

    )
    db.add(new_student)
    await db.commit()
    await db.refresh(new_student)

    return {"student": new_student, "password": raw_password}



async def get_all_students(db: AsyncSession):
    result = await db.execute(select(Student))
    return result.scalars().all()

async def get_student_by_id(db: AsyncSession, student_id: int) -> Student | None:
    result = await db.execute(select(Student).where(Student.id == student_id))
    return result.scalar_one_or_none()

async def update_student(db: AsyncSession, student_id: int, data: StudentUpdate) -> Student | None:
    student = await get_student_by_id(db, student_id)
    if not student:
        return None
    for key, value in data.dict(exclude_unset=True).items():
        setattr(student, key, value)
    await db.commit()
    await db.refresh(student)
    return student

async def delete_student(db: AsyncSession, student_id: int) -> dict:
    result = await db.execute(select(Student).where(Student.id == student_id))
    student = result.scalar_one_or_none()

    if not student:
        raise HTTPException(status_code=404, detail="O'quvchi topilmadi")

    await db.delete(student)
    await db.commit()

    return {"detail": "O'quvchi muvaffaqiyatli o'chirildi"}

async def get_student_by_login(db, login: str):
    result = await db.execute(select(Student).where(Student.login == login))
    return result.scalar_one_or_none()