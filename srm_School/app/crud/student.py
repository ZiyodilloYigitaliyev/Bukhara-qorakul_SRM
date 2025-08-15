from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.models.student import Student
from app.schemas.student import StudentCreate, StudentCreate, StudentOut, StudentUpdate, StudentOutWithPassword
from fastapi import HTTPException
from app.api.routes import auth, students
from app.core.utils import *

from app.db.database import get_db

from sqlalchemy.exc import IntegrityError
from fastapi import HTTPException, status



async def create_student(db: AsyncSession, data: StudentCreate):
    login = data.login or f"{data.first_name.lower()}.{data.last_name.lower()}"
    raw_password = data.password or f"{login[:4]}#{login[-3:]}9"  # oddiy avtomatik generatsiya
    hashed_pw = hash_password(raw_password)

    new_student = Student(
        first_name=data.first_name,
        last_name=data.last_name,
        passport_number=data.passport_number,
        student_code=data.student_code,
        image_url=data.image_url,
        birth_date=data.birth_date,
        gender=data.gender,
        face_terminal_id=data.face_terminal_id,
        parent_father_name=data.parent_father_name,
        parent_father_phone=data.parent_father_phone,
        parent_mother_name=data.parent_mother_name,
        parent_mother_phone=data.parent_mother_phone,
        class_name=data.class_name,
        is_active=True if data.is_active is None else data.is_active,
        login=login,
        hashed_password=hashed_pw,
        school_id=data.school_id or 1
    )

    db.add(new_student)
    try:
        await db.commit()
        await db.refresh(new_student)
    except IntegrityError as e:
        await db.rollback()
        if 'students_login_key' in str(e.orig):
            raise HTTPException(status_code=409, detail="Login allaqachon mavjud")
        if 'students_student_code_key' in str(e.orig):
            raise HTTPException(status_code=409, detail="Student code allaqachon mavjud")
        if 'students_face_terminal_id_key' in str(e.orig):
            raise HTTPException(status_code=409, detail="Face Terminal ID allaqachon mavjud")
        raise HTTPException(status_code=400, detail="Noto‘g‘ri ma’lumotlar")

    return {
        "student": StudentOut.model_validate(new_student, from_attributes=True),
        "password": raw_password  # frontendga ko‘rsatish uchun
    }



async def get_all_students(db: AsyncSession):
    result = await db.execute(select(Student))
    return result.scalars().all()

async def get_student_by_id(db: AsyncSession, student_id: int) -> Student | None:
    result = await db.execute(select(Student).where(Student.id == student_id))
    return result.scalar_one_or_none()

async def get_student_by_face_id(db: AsyncSession, face_terminal_id: int):
    result = await db.execute(
        select(Student).where(Student.face_terminal_id == face_terminal_id)
    )
    return result.scalar_one_or_none()

async def update_student(db: AsyncSession, student_id: int, data: StudentCreate) -> Student | None:
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

async def get_student_credentials(db: AsyncSession, student_id: int):
    result = await db.execute(select(Student).where(Student.id == student_id))
    student = result.scalar_one_or_none()

    if not student:
        return None

    return {
        "student": StudentOut.model_validate(student).model_dump(),
        "password": student.password  # parol plaintext ko‘rinishda saqlanmoqda deb faraz qilamiz
    }

