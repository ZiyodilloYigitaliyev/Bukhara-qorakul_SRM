# app/api/routes/face_terminal.py
from fastapi import APIRouter, Request, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.database import get_db
from app.models.student import Student
from app.models.attendance import Attendance
from datetime import datetime, date as _date, time
from typing import Optional, List, Dict, Tuple
import os, json, asyncio, time as _time
import logging
import httpx

# Ixtiyoriy: o‘qituvchi modeli bo‘lsa
try:
    from app.models.teacher import Teacher
except Exception:
    Teacher = None

# SMS shablonlari (siz yozgan fayl)
from app.services.sms.sms_templates import (
    sms_keldi, sms_kechikib_keldi, sms_ketdi, sms_kelmagan
)

logger = logging.getLogger("uvicorn.error")
router = APIRouter(prefix="/face-terminal", tags=["Face Terminal"])

from app.core.config import settings

ESKIZ_BASE_URL = settings.ESKIZ_BASE_URL
ESKIZ_EMAIL = settings.ESKIZ_EMAIL
ESKIZ_PASSWORD = settings.ESKIZ_PASSWORD
ESKIZ_FROM = settings.ESKIZ_FROM




# Blok: daqiqalarda (default 240 = 4 soat). Test uchun 1 qo‘yib ko‘rishingiz mumkin.
BLOCK_MINUTES = int(os.getenv("FACE_BLOCK_MINUTES", "1"))

# Kechikish chegarasi (HH:MM). default 08:00
_LATE_HHMM = os.getenv("FACE_LATE_HHMM", "8:00")
try:
    _hh, _mm = map(int, _LATE_HHMM.split(":"))
    LATE_THRESHOLD = time(_hh, _mm)
except Exception:
    LATE_THRESHOLD = time(8, 0)

# dedupe (bir necha soniyada ketma-ket urish bo‘lsa skip)
_DEDUPE: Dict[Tuple[str, str], float] = {}
_DEDUPE_WINDOW_SEC = float(os.getenv("FACE_DEDUPE_SEC", "4"))

# =========================
#   Eskiz SMS (inline)
# =========================
_TOKEN: Optional[str] = None
_TOKEN_EXPIRES_AT: float = 0.0
_TOKEN_LOCK = asyncio.Lock()

def _normalize_uz_phone(raw: Optional[str]) -> Optional[str]:
    if not raw:
        return None
    digits = "".join(ch for ch in raw if ch.isdigit())
    if not digits:
        return None
    if digits.startswith("998") and len(digits) == 12:
        return digits
    if len(digits) == 9:              # 90xxxxxxx
        return "998" + digits
    if len(digits) == 10 and digits.startswith("0"):  # 0 90xxxxxxx
        return "998" + digits[1:]
    if len(digits) == 11 and digits.startswith("8"):  # 8 90xxxxxxx
        return "9" + digits
    if digits.startswith("998") and len(digits) > 12:
        return digits[:12]
    return None

async def _eskiz_login(client: "httpx.AsyncClient") -> str:
    """POST /api/auth/login → {data: {token}}"""
    global _TOKEN, _TOKEN_EXPIRES_AT
    r = await client.post(
        f"{ESKIZ_BASE_URL}/api/auth/login",
        data={"email": ESKIZ_EMAIL, "password": ESKIZ_PASSWORD},
        timeout=20
    )
    try:
        r.raise_for_status()
    except httpx.HTTPStatusError as e:
        raise RuntimeError(f"Eskiz login failed {r.status_code}: {r.text}") from e
    data = r.json()
    token = data.get("data", {}).get("token") or data.get("token")
    if not token:
        raise RuntimeError(f"Eskiz token not found in response: {data}")
    _TOKEN = token
    _TOKEN_EXPIRES_AT = _time.time() + 55*60  # ~55 min
    return _TOKEN

async def _eskiz_get_token(client: "httpx.AsyncClient") -> str:
    async with _TOKEN_LOCK:
        if _TOKEN and _time.time() < (_TOKEN_EXPIRES_AT - 60):
            return _TOKEN
        return await _eskiz_login(client)

async def _send_sms(phone_998: str, message: str):
    if not phone_998 or not message:
        raise RuntimeError("phone/message empty")

    async with httpx.AsyncClient() as client:
        token = await _eskiz_get_token(client)
        headers = {"Authorization": f"Bearer {token}"}

        # callback_url YO'Q
        payload = {
            "mobile_phone": phone_998,
            "message": message,
        }
        if ESKIZ_FROM:
            payload["from"] = ESKIZ_FROM

        # 1) JSON
        r = await client.post(
            f"{ESKIZ_BASE_URL}/api/message/sms/send",
            json=payload, headers=headers, timeout=25
        )

        # 401 → relogin
        if r.status_code == 401:
            token = await _eskiz_login(client)
            headers["Authorization"] = f"Bearer {token}"
            r = await client.post(
                f"{ESKIZ_BASE_URL}/api/message/sms/send",
                json=payload, headers=headers, timeout=25
            )

        # JSON rad etilsa → form-data fallback
        if r.status_code in (400, 415, 422):
            r = await client.post(
                f"{ESKIZ_BASE_URL}/api/message/sms/send",
                data=payload, headers=headers, timeout=25
            )

        if r.is_error:
            # FROM sabab xato bo'lsa, FROMsiz qayta urinib ko'ramiz
            if "from" in payload and r.status_code in (400, 422):
                payload2 = {"mobile_phone": phone_998, "message": message}
                r2 = await client.post(
                    f"{ESKIZ_BASE_URL}/api/message/sms/send",
                    json=payload2, headers=headers, timeout=25
                )
                if r2.is_error:
                    raise RuntimeError(f"Eskiz send failed {r.status_code}: {r.text}; retry {r2.status_code}: {r2.text}")
                return r2.json()
            raise RuntimeError(f"Eskiz send failed {r.status_code}: {r.text}")

        return r.json()



async def _send_bulk_sms(phones: List[str], message: str) -> dict:
    results = {}
    for raw in phones:
        normalized = _normalize_uz_phone(raw)
        if not normalized:
            results[raw] = {"ok": False, "error": "invalid_phone"}
            continue
        try:
            resp = await _send_sms(normalized, message)
            results[normalized] = {"ok": True, "resp": resp}
        except Exception as e:
            results[normalized or raw] = {"ok": False, "error": str(e)}
    return results


async def _notify_parents(student, text: str):
    # Avval ota raqami, agar yo‘q bo‘lsa – ona raqami
    phone = None
    father = getattr(student, "parent_father_phone", None)
    mother = getattr(student, "parent_mother_phone", None)

    if father:
        phone = father
    elif mother:
        phone = mother
    else:
        return  # hech kimga yuborilmaydi

    # _send_bulk_sms ro‘yxat kutadi
    asyncio.create_task(_send_bulk_sms([phone], text))

# =========================
#   Yordamchi
# =========================
def _parse_dt(dt_str: str) -> datetime:
    """
    "2025-09-09T20:24:56+05:00" yoki "YYYY-MM-DD HH:MM:SS"
    """
    try:
        return datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
    except Exception:
        try:
            return datetime.strptime(dt_str, "%Y-%m-%d %H:%M:%S")
        except Exception as e:
            raise ValueError(f"dateTime parse error: {dt_str}") from e

def _cols(model):
    return set(getattr(model.__table__, "columns").keys())

def _iso_hms(t: Optional[time]) -> Optional[str]:
    return t.strftime("%H:%M:%S") if t else None

def _attendance_out(a: Attendance) -> dict:
    """
    API uchun qulay, mos sarlavhalar:
      - left_time: DB dagi departure_time’ning aliasi
      - arrival_status: on_time/late (modelda bo‘lsa)
    """
    return {
        "id": a.id,
        "student_id": getattr(a, "student_id", None),
        "teacher_id": getattr(a, "teacher_id", None),
        "date": str(a.date) if a.date else None,
        "arrival_time": _iso_hms(a.arrival_time),
        "left_time": _iso_hms(getattr(a, "departure_time", None)),
        "late_minutes": getattr(a, "late_minutes", None),
        "arrival_status": getattr(a, "arrival_status", None),
        "is_present": getattr(a, "is_present", None),
        "status": getattr(a, "status", None),
    }

# ---- Tezkor diagnostika (Postman’ga mos test) ----
# @router.post("/sms-test")
# async def sms_test(number: str, message: str = "Eskiz API ping", _db: AsyncSession = Depends(get_db)):
#     norm = _normalize_uz_phone(number)
#     if not norm:
#         raise HTTPException(status_code=400, detail="invalid phone; use 9989XXXXXXXX")
#     try:
#         resp = await _send_sms(norm, message)
#         return {"ok": True, "to": norm, "resp": resp}
#     except Exception as e:
#         return {"ok": False, "to": norm, "error": str(e), "base_url": ESKIZ_BASE_URL, "from": ESKIZ_FROM}

# =========================
#   Face ID log endpoint
# =========================
@router.post("/log")
async def receive_log(request: Request, db: AsyncSession = Depends(get_db)):
    # --- Body parsing ---
    ctype = (request.headers.get("content-type") or "").lower()
    if ctype.startswith("application/json"):
        raw = await request.body()
        data = json.loads(raw.decode("utf-8", errors="ignore") or "{}")
    elif ctype.startswith("multipart/form-data"):
        form = await request.form()
        part = form.get("AccessControllerEvent") or form.get("json") or form.get("payload")
        if part is None:
            raise HTTPException(status_code=400, detail="AccessControllerEvent not found in form-data")
        text = (await part.read()).decode("utf-8", errors="ignore") if hasattr(part, "read") else str(part)
        data = json.loads(text or "{}")
    else:
        raise HTTPException(status_code=400, detail=f"Unsupported Content-Type: {ctype}")

    # --- Event object ---
    event = data.get("AccessControllerEvent") or data

    # Faqat AccessControllerEvent + subEventType=75
    evt_type = event.get("eventType") or data.get("eventType")
    if evt_type and str(evt_type) not in ("AccessControllerEvent",):
        return {"ok": True, "skip": True, "reason": f"eventType={evt_type}"}

    sub_event_type = int(event.get("subEventType", -1))
    if sub_event_type != 75:
        return {"ok": True, "skip": True, "reason": f"subEventType={sub_event_type}"}

    # --- Maydonlar ---
    name_val = (event.get("name") or "").strip()
    emp_str = (event.get("employeeNoString") or event.get("employeeNo") or "").strip()
    if not emp_str:
        return {"ok": True, "skip": True, "reason": "employeeNoString missing"}

    # dedupe window
    key = (name_val, emp_str)
    now_ts = datetime.utcnow().timestamp()
    last_ts = _DEDUPE.get(key, 0.0)
    if now_ts - last_ts < _DEDUPE_WINDOW_SEC:
        return {"ok": True, "skip": True, "reason": "dedupe_window"}
    _DEDUPE[key] = now_ts

    # Sana/vaqt
    dt_str = event.get("dateTime") or data.get("dateTime")
    if not dt_str:
        raise HTTPException(status_code=400, detail="dateTime yo‘q")
    dt = _parse_dt(dt_str)
    d = dt.date()
    t = dt.time()

    # Kechikish (daqiqada)
    if t > LATE_THRESHOLD:
        late_minutes = int((datetime.combine(d, t) - datetime.combine(d, LATE_THRESHOLD)).total_seconds() // 60)
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
    if face_id is not None:
        student = await db.scalar(select(Student).where(Student.face_terminal_id == face_id))
        if (student is None) and (Teacher is not None):
            teacher = await db.scalar(select(Teacher).where(Teacher.face_terminal_id == face_id))

    if not student and not teacher:
        raise HTTPException(status_code=404, detail=f"Foydalanuvchi topilmadi (employeeNoString={emp_str})")

    # Dinamik ustunlar
    att_cols = _cols(Attendance) if Attendance else set()
    has_departure = "departure_time" in att_cols
    has_status = "status" in att_cols         # umumiy holat (mas: 'left')
    has_is_present = "is_present" in att_cols
    has_school = "school_id" in att_cols
    has_user_type = "user_type" in att_cols
    has_arrival_status = "arrival_status" in att_cols  # on_time/late

    # =============================
    #         O'QUVCHI oqimi
    # =============================
    if student:
        existing = await db.scalar(
            select(Attendance).where(
                Attendance.student_id == student.id,
                Attendance.date == d
            )
        )

        # 1-urinish: KELDI
        if existing is None:
            payload = {
                "student_id": student.id,
                "date": d,
                "arrival_time": t,
                "late_minutes": late_minutes,
            }
            if has_is_present:     payload["is_present"] = True
            if has_user_type:      payload["user_type"] = event.get("userType") or "student"
            if has_arrival_status: payload["arrival_status"] = arrival_status
            if has_school:         payload["school_id"] = getattr(student, "school_id", None)

            att = Attendance(**payload)
            db.add(att)
            await db.commit()
            await db.refresh(att)

            # SMS: keldi vs kechikib keldi
            try:
                msg = sms_kechikib_keldi(student, late_minutes) if late_minutes > 0 else sms_keldi(student, t.strftime("%H:%M"))
                await _notify_parents(student, msg)
            except Exception:
                pass

            return {"ok": True, "attendance": _attendance_out(att), "role": "student"}

        # 2-urinish: blok yoki KETDI
        if has_departure and getattr(existing, "departure_time", None) is None:
            # agar arrival yo'q bo'lsa, uni to'g'rilab qo'yamiz
            if existing.arrival_time is None:
                existing.arrival_time = t
                existing.late_minutes = late_minutes
                if has_arrival_status:
                    existing.arrival_status = arrival_status
                await db.commit()
                await db.refresh(existing)
                return {"ok": True, "attendance": _attendance_out(existing), "role": "student"}

            diff_min = int((datetime.combine(d, t) - datetime.combine(d, existing.arrival_time)).total_seconds() // 60)
            if diff_min < BLOCK_MINUTES:
                return {"ok": True, "skip": True, "reason": "block_minutes", "diff_min": diff_min, "need_min": BLOCK_MINUTES}

            # Ketish
            existing.departure_time = t
            if has_status:
                existing.status = "left"
            await db.commit()
            await db.refresh(existing)

            # SMS: ketdi
            try:
                msg = sms_ketdi(student, t.strftime("%H:%M"))
                await _notify_parents(student, msg)
            except Exception:
                pass

            return {"ok": True, "attendance": _attendance_out(existing), "role": "student"}

        return {"ok": True, "skip": True, "reason": "no_departure_or_already_set"}

    # =============================
    #         O'QITUVCHI oqimi
    # =============================
    if teacher:
        existing = await db.scalar(
            select(Attendance).where(
                Attendance.teacher_id == teacher.id,
                Attendance.date == d
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
            if has_user_type:      payload["user_type"] = event.get("userType") or "teacher"
            if has_arrival_status: payload["arrival_status"] = arrival_status
            if has_school:         payload["school_id"] = getattr(teacher, "school_id", None)

            att = Attendance(**payload)
            db.add(att)
            await db.commit()
            await db.refresh(att)
            return {"ok": True, "attendance": _attendance_out(att), "role": "teacher"}
        else:
            if has_departure and getattr(existing, "departure_time", None) is None:
                base = existing.arrival_time or t
                diff_min = int((datetime.combine(d, t) - datetime.combine(d, base)).total_seconds() // 60)
                if diff_min < BLOCK_MINUTES:
                    return {"ok": True, "skip": True, "reason": "block_minutes_teacher", "diff_min": diff_min, "need_min": BLOCK_MINUTES}
                existing.departure_time = t
                if has_status:
                    existing.status = "left"
                await db.commit()
                await db.refresh(existing)
                return {"ok": True, "attendance": _attendance_out(existing), "role": "teacher"}
            return {"ok": True, "skip": True, "reason": "no_departure_or_already_set_teacher"}

    return {"ok": True, "skip": True, "reason": "unhandled"}

# =======================================
#   Kelmadi (no-show) batch bildirishi
# =======================================
@router.post("/notify-no-show")
async def notify_no_show(
    db: AsyncSession = Depends(get_db),
    the_date: Optional[str] = Query(None, description="YYYY-MM-DD; default: today"),
    only_active: bool = Query(True),
    dry_run: bool = Query(False, description="True bo'lsa SMS yubormaydi, faqat ro'yxat qaytaradi"),
):
    # Sana
    if the_date:
        try:
            d = datetime.fromisoformat(the_date).date()
        except Exception:
            raise HTTPException(status_code=400, detail="the_date formati noto'g'ri (YYYY-MM-DD)")
    else:
        d = datetime.utcnow().date()

    # Bugun kelmagan o'quvchilar (attendance yo'q)
    subq = select(Attendance.student_id).where(Attendance.date == d)
    q = select(Student)
    if only_active:
        q = q.where(Student.is_active.is_(True))
    q = q.where(~Student.id.in_(subq))
    students = (await db.execute(q)).scalars().all()

    sent, skipped = [], []
    if dry_run:
        for s in students:
            sent.append({"student_id": s.id, "name": f"{s.first_name} {s.last_name}"})
        return {"date": str(d), "count": len(sent), "dry_run": True, "students": sent}

    for s in students:
        phones = []
        if s.parent_father_phone: phones.append(s.parent_father_phone)
        if s.parent_mother_phone: phones.append(s.parent_mother_phone)
        if not phones:
            skipped.append({"student_id": s.id, "reason": "no_parent_phone"})
            continue
        try:
            msg = sms_kelmagan(s)
            res = await _send_bulk_sms(phones, msg)
            sent.append({"student_id": s.id, "resp": res})
        except Exception as e:
            skipped.append({"student_id": s.id, "reason": str(e)})

    return {"date": str(d), "sent": sent, "skipped": skipped, "counts": {"sent": len(sent), "skipped": len(skipped)}}

import os, json
from datetime import datetime

# ... (mavjud importlar saqlansin)

# Xom POST loglar joyi: .env da FACE_RAW_LOG_DIR berib qo‘ysangiz bo‘ladi
FACE_RAW_LOG_DIR = os.getenv("FACE_RAW_LOG_DIR", "logs/face_raw")

@router.post("/dump")
async def dump_raw_post(request: Request):
    """
    Nima POST qilinsa, o‘sha xom bodyni txt faylga yozib qo‘yadi.
    Har kuni bitta faylga append bo‘ladi: logs/face_raw/2025-09-16.txt
    """
    # meta
    ctype = (request.headers.get("content-type") or "")
    client_ip = request.client.host if request.client else None
    ua = request.headers.get("user-agent")

    # xom body
    body_bytes = await request.body()
    # UTF-8 bo‘lmasa ham yozila olishi uchun "latin-1" fallback
    try:
        body_text = body_bytes.decode("utf-8")
    except UnicodeDecodeError:
        body_text = body_bytes.decode("latin-1", errors="ignore")

    # fayl nomi: kunlik
    utc_now = datetime.utcnow()
    day_str = utc_now.strftime("%Y-%m-%d")
    ts = utc_now.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3] + "Z"

    os.makedirs(FACE_RAW_LOG_DIR, exist_ok=True)
    file_path = os.path.join(FACE_RAW_LOG_DIR, f"{day_str}.txt")

    # yoziladigan blok (ajratkichlar bilan)
    header = {
        "time": ts,
        "ip": client_ip,
        "content_type": ctype,
        "user_agent": ua,
        "content_length": len(body_bytes),
    }
    block = (
        "\n==================== POST ====================\n"
        + json.dumps(header, ensure_ascii=False)
        + "\n----------------------------------------------\n"
        + body_text
        + "\n================== END POST ==================\n"
    )

    # yozish (oddiy sync; kichik fayllar uchun yetarli)
    with open(file_path, "a", encoding="utf-8") as f:
        f.write(block)

    return {"ok": True, "saved_to": file_path, "bytes": len(body_bytes)}
