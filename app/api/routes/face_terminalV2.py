from fastapi import APIRouter, Request, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_
from datetime import datetime, time as dt_time, timedelta, timezone
import json, os

from app.db.database import get_db
from app.models.student import Student
from app.models.attendance import Attendance
try:
    from app.models.teacher import Teacher
except Exception:
    Teacher = None

router = APIRouter(prefix="/face-terminal", tags=["Face Terminal"])

# ---- sozlamalar (xohlasangiz .env orqali) ----
BLOCK_MINUTES = int(os.getenv("FACE_BLOCK_MINUTES", "4"))        # kelganidan keyin necha daqiqada "ketdi" yozishga ruxsat
LATE_HHMM = os.getenv("FACE_LATE_HHMM", "08:00")                  # kechikish chegarasi
LOCAL_TZ = timezone(timedelta(hours=int(os.getenv("LOCAL_TZ_HOURS", "5"))))  # +05:00 default

hh, mm = (int(x) for x in LATE_HHMM.split(":"))
LATE_THRESHOLD = dt_time(hh, mm)

def _parse_dt_any(s: str) -> datetime:
    # "2025-09-17T02:56:26+08:00" yoki "YYYY-MM-DD HH:MM:SS"
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00"))
    except Exception:
        return datetime.strptime(s, "%Y-%m-%d %H:%M:%S")

def _to_local(dt: datetime) -> datetime:
    return dt.astimezone(LOCAL_TZ) if dt.tzinfo else dt.replace(tzinfo=timezone.utc).astimezone(LOCAL_TZ)

def _cols(model):
    return set(getattr(model.__table__, "columns").keys())

def _name_matches(person, posted_name: str) -> bool:
    if not posted_name or not person:
        return False
    p = posted_name.strip().lower()
    first = (getattr(person, "first_name", "") or "").lower()
    last = (getattr(person, "last_name", "") or "").lower()
    full = f"{first} {last}".strip()
    return p in {first, last, full}

async def _extract_event(request: Request) -> dict:
    """event_log | AccessControllerEvent | json | payload dagidan JSON ni ajratadi va AccessControllerEvent obyektini qaytaradi."""
    ctype = (request.headers.get("content-type") or "").lower()
    data = {}
    if ctype.startswith("multipart/form-data"):
        form = await request.form()
        part = form.get("event_log") or form.get("AccessControllerEvent") or form.get("json") or form.get("payload")
        if part is None:
            raise HTTPException(status_code=400, detail="event_log yo‘q (form-data)")
        text = (await part.read()).decode("utf-8", errors="ignore") if hasattr(part, "read") else str(part)
        data = json.loads(text or "{}")
    elif ctype.startswith("application/json"):
        raw = await request.body()
        data = json.loads(raw.decode("utf-8", errors="ignore") or "{}")
    else:
        # boshqa holatlar: xom bodyni ham JSON deb ko‘ramiz
        raw = await request.body()
        try:
            data = json.loads(raw.decode("utf-8", errors="ignore"))
        except Exception:
            raise HTTPException(status_code=400, detail=f"Unsupported Content-Type: {ctype}")

    # ayrim modellarda butun paket ichida AccessControllerEvent mavjud
    evt = data.get("AccessControllerEvent") or data
    return evt

@router.post("/logV2")
async def receive_log(request: Request, db: AsyncSession = Depends(get_db)):
    evt = await _extract_event(request)

    # Tekshirish uchun kerak bo'lgan maydonlar
    posted_name = (evt.get("name") or "").strip()
    emp_str = str(evt.get("employeeNoString") or evt.get("employeeNo") or "").strip()
    sub_event = int(evt.get("subEventType", -1))
    if not emp_str:
        return {"ok": True, "skip": True, "reason": "employeeNoString missing"}
    if sub_event != 75:  # access pass success
        return {"ok": True, "skip": True, "reason": f"subEventType={sub_event}"}

    # Sana/vaqt
    root = {}  # ayrim firmwarelarda dateTime ota obyektida bo‘ladi
    try:
        # request.body() dan olingan asl JSON topqidagicha bo‘lgan — unga yetishish uchun...
        # /extract_event ichida faqat evt qaytdi; dateTime esa ko‘pincha ota JSON’da bo‘ladi.
        # Shu sababli qaytadan formni o‘qimaymiz; Hik loglarida evt ichida bo‘lmasa ham, POST ichida bo‘lgan vaqtni ishlatamiz.
        root_dt = (request.headers.get("x-device-datetime") or None)
    except Exception:
        root_dt = None

    # Hik loglarida ko‘pincha dateTime ota-level’da: event_log.dateTime
    # extract_event evt ni qaytargan, shuning uchun parent yo‘q — lekin ko‘pchilik firmware evt ichida ham dateTime beradi, tekshiramiz:
    dt_str = evt.get("dateTime")
    if not dt_str:
        # fallback: query param, header yoki hozirgi vaqt
        dt_local = _to_local(datetime.now(timezone.utc))
    else:
        dt_local = _to_local(_parse_dt_any(dt_str))

    d = dt_local.date()
    t = dt_local.time()

    # Kechikish
    if t > LATE_THRESHOLD:
        late_minutes = int((_to_local(datetime.combine(d, t)) - _to_local(datetime.combine(d, LATE_THRESHOLD))).total_seconds() // 60)
        arrival_status = "late"
    else:
        late_minutes = 0
        arrival_status = "on_time"

    # Kim?
    try:
        face_id = int(emp_str)
    except ValueError:
        face_id = None

    student = None
    teacher = None

    # 1) ID bo‘yicha moslash
    if face_id is not None:
        student = await db.scalar(select(Student).where(Student.face_terminal_id == face_id))
        if (student is None) and (Teacher is not None):
            teacher = await db.scalar(select(Teacher).where(Teacher.face_terminal_id == face_id))

    # 2) ID topilmasa — posted name bo‘yicha moslash (ixtiyoriy)
    if not student and not teacher and posted_name:
        # first_name/last_name bo‘yicha sodda qidiruv
        student = await db.scalar(
            select(Student).where(
                or_(Student.first_name.ilike(posted_name), Student.last_name.ilike(posted_name))
            )
        )
        if (student is None) and (Teacher is not None):
            teacher = await db.scalar(
                select(Teacher).where(
                    or_(Teacher.first_name.ilike(posted_name), Teacher.last_name.ilike(posted_name))
                )
            )

    if not student and not teacher:
        raise HTTPException(status_code=404, detail=f"Foydalanuvchi topilmadi: name={posted_name!r}, employeeNoString={emp_str!r}")

    # (ixtiyoriy) nom mos kelishini ham tekshiramiz — mismatch bo‘lsa log/skip qilishingiz mumkin
    if student and posted_name and not _name_matches(student, posted_name):
        # nom mos emas, lekin ID mos — xabar sifatida qaytaramiz
        name_warning = "student_name_mismatch"
    elif teacher and posted_name and not _name_matches(teacher, posted_name):
        name_warning = "teacher_name_mismatch"
    else:
        name_warning = None

    # Attendance modelining dinamik ustunlarini tekshiramiz
    att_cols = _cols(Attendance)
    has_departure = "departure_time" in att_cols
    has_status = "status" in att_cols
    has_is_present = "is_present" in att_cols
    has_arrival_status = "arrival_status" in att_cols
    has_school = "school_id" in att_cols
    has_user_type = "user_type" in att_cols

    # ---- STUDENT oqimi ----
    if student:
        existing = await db.scalar(
            select(Attendance).where(
                Attendance.student_id == student.id,
                Attendance.date == d,
            )
        )
        if existing is None:
            payload = {
                "student_id": student.id,
                "date": d,
                "arrival_time": t,
                "late_minutes": late_minutes,
            }
            if has_is_present:     payload["is_present"] = True
            if has_arrival_status: payload["arrival_status"] = arrival_status
            if has_school:         payload["school_id"] = getattr(student, "school_id", None)
            if has_user_type:      payload["user_type"] = "student"

            att = Attendance(**payload)
            db.add(att)
            await db.commit()
            await db.refresh(att)
            return {"ok": True, "role": "student", "name_warning": name_warning, "attendance": {
                "id": att.id, "date": str(att.date), "arrival_time": str(att.arrival_time), "late_minutes": att.late_minutes
            }}

        # KETDI (agar departure_time yo‘q va blokdan o‘tgan bo‘lsa)
        if has_departure and getattr(existing, "departure_time", None) is None:
            base = existing.arrival_time or t
            diff_min = int((datetime.combine(d, t) - datetime.combine(d, base)).total_seconds() // 60)
            if diff_min < BLOCK_MINUTES:
                return {"ok": True, "role": "student", "skip": True, "reason": "block_minutes", "diff_min": diff_min, "need_min": BLOCK_MINUTES}
            existing.departure_time = t
            if has_status: existing.status = "left"
            await db.commit()
            await db.refresh(existing)
            return {"ok": True, "role": "student", "attendance": {
                "id": existing.id, "date": str(existing.date),
                "arrival_time": str(existing.arrival_time),
                "departure_time": str(existing.departure_time)
            }}

        return {"ok": True, "role": "student", "skip": True, "reason": "no_departure_or_already_set"}

    # ---- TEACHER oqimi ----
    if teacher:
        existing = await db.scalar(
            select(Attendance).where(
                Attendance.teacher_id == teacher.id,
                Attendance.date == d,
            )
        )
        if existing is None:
            payload = {
                "teacher_id": teacher.id,
                "date": d,
                "arrival_time": t,
                "late_minutes": late_minutes,
            }
            if has_is_present:     payload["is_present"] = True
            if has_arrival_status: payload["arrival_status"] = arrival_status
            if has_school:         payload["school_id"] = getattr(teacher, "school_id", None)
            if has_user_type:      payload["user_type"] = "teacher"

            att = Attendance(**payload)
            db.add(att)
            await db.commit()
            await db.refresh(att)
            return {"ok": True, "role": "teacher", "name_warning": name_warning, "attendance": {
                "id": att.id, "date": str(att.date), "arrival_time": str(att.arrival_time), "late_minutes": att.late_minutes
            }}

        if has_departure and getattr(existing, "departure_time", None) is None:
            base = existing.arrival_time or t
            diff_min = int((datetime.combine(d, t) - datetime.combine(d, base)).total_seconds() // 60)
            if diff_min < BLOCK_MINUTES:
                return {"ok": True, "role": "teacher", "skip": True, "reason": "block_minutes", "diff_min": diff_min, "need_min": BLOCK_MINUTES}
            existing.departure_time = t
            if has_status: existing.status = "left"
            await db.commit()
            await db.refresh(existing)
            return {"ok": True, "role": "teacher", "attendance": {
                "id": existing.id, "date": str(existing.date),
                "arrival_time": str(existing.arrival_time),
                "departure_time": str(existing.departure_time)
            }}

        return {"ok": True, "role": "teacher", "skip": True, "reason": "no_departure_or_already_set"}

    return {"ok": True, "skip": True, "reason": "unhandled"}
