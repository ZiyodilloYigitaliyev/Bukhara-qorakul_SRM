from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.crud.credentials import gen_password
from app.models.teacher import Teacher
from app.schemas.teacher import CreateTeacher

# app/crud/teacher.py
import re, secrets, string, unicodedata
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError
from fastapi import HTTPException

from app.models.teacher import Teacher
from app.schemas.teacher import TeacherCreate
from app.core.utils import hash_password
from app.crud.credentials import gen_password, make_unique_login_for_model

def _ascii_slug(text: str) -> str:
    # Aksentlarni tushirish va faqat [a-z0-9 .] qoldirish
    text = unicodedata.normalize("NFKD", text)
    text = "".join(c for c in text if not unicodedata.combining(c))
    text = text.lower()
    text = re.sub(r"[^a-z0-9]+", ".", text).strip(".")
    return text or "teacher"


async def _make_unique_login(db: AsyncSession, first_name: str, last_name: str) -> str:
    base = _ascii_slug(f"{first_name}.{last_name}")[:28]  # suffix uchun joy qoldiramiz
    # bazani bo'sh bo'lsa darhol qaytaramiz
    exists = await db.execute(select(Teacher.id).where(Teacher.login == base))
    if exists.first() is None:
        return base

    # shu prefiks bilan mavjud loginlarni olib, birinchi bo'sh suffixni topamiz
    res = await db.execute(select(Teacher.login).where(Teacher.login.ilike(f"{base}%")))
    taken = set(res.scalars().all())
    for i in range(1, 1000):
        cand = f"{base}{i}"
        if cand not in taken:
            return cand
    # agar hamon to'qnashsa — random fallback
    return f"{base}{secrets.randbelow(10_000)}"


def _gen_password(length: int = 12) -> str:
    # Kamida 1 ta kichik, 1 ta katta, 1 ta raqam bo'lsin
    rng = secrets.SystemRandom()
    core = (
        rng.choice(string.ascii_lowercase)
        + rng.choice(string.ascii_uppercase)
        + rng.choice(string.digits)
    )
    alphabet = string.ascii_letters + string.digits
    core += "".join(rng.choice(alphabet) for _ in range(length - len(core)))
    pw = list(core)
    rng.shuffle(pw)
    return "".join(pw)


async def create_teacher(db: AsyncSession, data: TeacherCreate):
    # Pydantic v2 model_dump(), aks holda dict()
    payload = data.model_dump() if hasattr(data, "model_dump") else data.dict()

    # 1) LOGIN: agar kelmasa — ism/familiyadan avto-generatsiya
    if not payload.get("login"):
        payload["login"] = await _make_unique_login(
            db, payload.get("first_name", ""), payload.get("last_name", "")
        )

    # 2) PASSWORD: agar kelmasa — avto-generatsiya
    plain_password = payload.pop("password", None) or _gen_password()

    # 3) HASH va saqlash
    payload["hashed_password"] = hash_password(plain_password)

    teacher = Teacher(**payload)
    db.add(teacher)

    try:
        await db.commit()
    except IntegrityError as e:
        await db.rollback()
        s = str(e).lower()

        # login kolliziya bo'lsa, bitta marta qayta urinib ko'ramiz
        if "login" in s and ("duplicate" in s or "unique" in s):
            payload["login"] = await _make_unique_login(
                db, payload.get("first_name", ""), payload.get("last_name", "")
            )
            teacher = Teacher(**payload)
            db.add(teacher)
            try:
                await db.commit()
            except IntegrityError:
                await db.rollback()
                raise HTTPException(status_code=400, detail="login band, qayta urinib ko'ring.")

        else:
            msg = "Teacher yaratib bo'lmadi: "
            if "phone_number" in s and ("duplicate" in s or "unique" in s):
                msg += "phone_number allaqachon band."
            elif "face_terminal_id" in s and ("duplicate" in s or "unique" in s):
                msg += "face_terminal_id allaqachon band."
            else:
                msg += "unique cheklov buzildi."
            raise HTTPException(status_code=400, detail=msg)

    await db.refresh(teacher)

    # ⚠️ Admin ko'rishi uchun vaqtincha plain parolni qaytarish foydali.
    # Agar API sxemangiz TeacherOut qaytarsa, routerda o'rab yuboring (quyida).
    return {"teacher": teacher, "temp_password": plain_password}


async def get_all_teachers(db: AsyncSession) -> list[Teacher]:
    result = await db.execute(select(Teacher))
    return list(result.scalars().all())

async def get_teacher_by_id(db: AsyncSession, teacher_id: int) -> Teacher | None:
    result = await db.execute(select(Teacher).where(Teacher.id == teacher_id))
    return result.scalar_one_or_none()

async def reset_teacher_credentials(
    db: AsyncSession,
    teacher_id: int,
    regenerate_login: bool = False,
) -> tuple[Teacher, str]:
    q = select(Teacher).where(Teacher.id == teacher_id)
    res = await db.execute(q)
    teacher = res.scalar_one_or_none()
    if not teacher:
        raise HTTPException(status_code=404, detail="Teacher topilmadi")

    # Loginni qayta generatsiya qilish ixtiyoriy
    if regenerate_login:
        teacher.login = await make_unique_login_for_model(db, Teacher, teacher.first_name, teacher.last_name, maxlen=50)

    # Parolni doim qayta generatsiya qilamiz
    temp_password = gen_password()
    teacher.hashed_password = hash_password(temp_password)

    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=409, detail="Login unique cheklovi urildi, qayta urinib ko‘ring.")

    await db.refresh(teacher)
    return teacher, temp_password