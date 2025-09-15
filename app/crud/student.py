# app/crud/student.py
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.exc import IntegrityError
from fastapi import HTTPException, status
from sqlalchemy.inspection import inspect as sa_inspect
import re, secrets, string

from app.models.student import Student
from app.schemas.student import StudentCreate, StudentUpdate, StudentOut, StudentOutWithPassword
from app.core.utils import hash_password


def _slugify(s: str) -> str:
    s = s.strip().lower()
    s = re.sub(r"[^a-z0-9]+", ".", s)
    s = re.sub(r"\.+", ".", s).strip(".")
    return s or "user"

async def _make_unique_login(db: AsyncSession, base_login: str) -> str:
    candidate = base_login
    i = 1
    while True:
        res = await db.execute(select(Student.id).where(Student.login == candidate))
        if res.scalar_one_or_none() is None:
            return candidate
        i += 1
        candidate = f"{base_login}-{i}"

def _gen_password(length: int = 10) -> str:
    alphabet = string.ascii_letters + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))

def _filter_model_kwargs(model, payload: dict) -> dict:
    """
    Modelda yo‘q bo‘lgan kalitlar (masalan class_name) avtomatik chiqarib tashlanadi.
    """
    cols = {c.key for c in sa_inspect(model).mapper.column_attrs}
    return {k: v for k, v in payload.items() if k in cols}

async def create_student(db: AsyncSession, data: StudentCreate) -> StudentOutWithPassword:
    # 1) login (agar payloadda bo‘lsa o‘shani ishlatamiz, bo‘lmasa avto-gen)
    desired_login = (data.login or "").strip()
    if desired_login:
        base_login = _slugify(desired_login)
    else:
        base_login = _slugify(f"{data.first_name}.{data.last_name}")
    login = await _make_unique_login(db, base_login)

    # 2) parol (agar payloadda bo‘lsa — ishlatamiz, aks holda avto-gen)
    incoming_pw = (data.password or "").strip()
    raw_password = incoming_pw if incoming_pw else _gen_password(10)
    hashed_pw = hash_password(raw_password)

    # 3) Pydantic -> dict
    base = data.model_dump(exclude_none=True)
    base.pop("password", None)   # hech qachon bevosita saqlamaymiz
    base["login"] = login

    # --- Parol ustuni nomini modelga qarab moslaymiz ---
    model_cols = {c.key for c in sa_inspect(Student).mapper.column_attrs}
    if "password_hash" in model_cols:
        base["password_hash"] = hashed_pw
    elif "hashed_password" in model_cols:
        base["hashed_password"] = hashed_pw
    else:
        # Modelda parol uchun ustun topilmadi
        raise HTTPException(500, "Student modelida parol ustuni topilmadi (password_hash/hashed_password).")

    # ⚠️ class_name, add_date va boshqalar modelda bo‘lmasa avtomatik tashlab yuboriladi
    model_kwargs = _filter_model_kwargs(Student, base)

    new_student = Student(**model_kwargs)
    db.add(new_student)

    try:
        await db.commit()
    except IntegrityError as e:
        await db.rollback()
        s = str(getattr(e, "orig", e))
        # Constraint nomlari DB va migratsiyaga qarab farq qiladi — bir nechta variantni qamrab olamiz:
        if any(k in s for k in ["uq_students_login", "students_login_key", "login_key"]):
            raise HTTPException(409, "Login allaqachon mavjud")
        if any(k in s for k in ["uq_students_code", "students_student_code_key", "student_code_key"]):
            raise HTTPException(409, "Student code allaqachon mavjud")
        if any(k in s for k in ["uq_students_face_terminal_id", "students_face_terminal_id_key", "face_terminal_id_key"]):
            raise HTTPException(409, "Face Terminal ID allaqachon mavjud")
        raise HTTPException(400, "Noto‘g‘ri ma’lumotlar")

    # 4) relationship xavfsiz yuklash (agar 'school' mavjud bo‘lsa)
    opts = []
    if hasattr(Student, "school"):
        opts.append(selectinload(Student.school))

    result = await db.execute(
        select(Student).options(*opts).where(Student.id == new_student.id)
    )
    loaded = result.scalar_one()

    # 5) Pydantic v2: from_orm emas, model_validate
    return StudentOutWithPassword(
        student=StudentOut.model_validate(loaded),
        password=raw_password  # faqat create javobida ko‘rsatamiz
    )

async def get_all_students(db: AsyncSession) -> list[StudentOut]:
    opts = []
    if hasattr(Student, "school"):
        opts.append(selectinload(Student.school))

    result = await db.execute(
        select(Student).options(*opts).order_by(Student.id.desc())
    )
    return [StudentOut.model_validate(s) for s in result.scalars().all()]

async def get_all_students(db: AsyncSession) -> list[StudentOut]:
    result = await db.execute(
        select(Student).options(selectinload(Student.school)).order_by(Student.id.desc())
    )
    return [StudentOut.from_orm(s) for s in result.scalars().all()]

async def get_student_by_id(db: AsyncSession, student_id: int) -> Student | None:
    result = await db.execute(select(Student).where(Student.id == student_id))
    return result.scalar_one_or_none()

async def get_student_out_by_id(db: AsyncSession, student_id: int) -> StudentOut | None:
    result = await db.execute(
        select(Student).options(selectinload(Student.school)).where(Student.id == student_id)
    )
    s = result.scalar_one_or_none()
    return StudentOut.from_orm(s) if s else None

async def update_student(db: AsyncSession, student_id: int, data: StudentUpdate) -> StudentOut | None:
    result = await db.execute(select(Student).where(Student.id == student_id))
    student = result.scalar_one_or_none()
    if not student:
        return None

    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(student, k, v)

    await db.commit()
    result = await db.execute(
        select(Student).options(selectinload(Student.school)).where(Student.id == student_id)
    )
    student = result.scalar_one_or_none()
    return StudentOut.from_orm(student) if student else None

async def delete_student(db: AsyncSession, student_id: int) -> dict:
    result = await db.execute(select(Student).where(Student.id == student_id))
    student = result.scalar_one_or_none()
    if not student:
        raise HTTPException(status_code=404, detail="O'quvchi topilmadi")
    await db.delete(student)
    await db.commit()
    return {"detail": "O'quvchi muvaffaqiyatli o'chirildi"}

async def reset_student_credentials(
    db: AsyncSession,
    student_id: int,
    regenerate_login: bool = False,
) -> tuple[Student, str]:
    q = select(Student).where(Student.id == student_id)
    res = await db.execute(q)
    student = res.scalar_one_or_none()
    if not student:
        raise HTTPException(status_code=404, detail="Student topilmadi")

    if regenerate_login:
        base_login = _slugify(f"{student.first_name}.{student.last_name}")[:50]
        student.login = await _make_unique_login(db, base_login)

    temp_password = _gen_password()
    student.hashed_password = hash_password(temp_password)

    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=409, detail="Login unique cheklovi urildi, qayta urinib ko‘ring.")

    await db.refresh(student)
    return student, temp_password