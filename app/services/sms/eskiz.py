# app/services/sms/eskiz.py
import os
import re
import asyncio
import httpx
from typing import Optional, Dict

from app.core.config import settings

ESKIZ_BASE_URL = settings.ESKIZ_BASE_URL
ESKIZ_EMAIL = settings.ESKIZ_EMAIL
ESKIZ_PASSWORD = settings.ESKIZ_PASSWORD
ESKIZ_FROM = settings.ESKIZ_FROM

_token_lock = asyncio.Lock()
_token_cache: Dict[str, str] = {}  # {"access_token": "..."}

def _clean_uz_phone(phone: str) -> Optional[str]:
    """999XXXXXXX yoki 9989XXXXXXXX formatga tozalaydi (plus va bo‘shliqlarsiz)."""
    if not phone:
        return None
    digits = re.sub(r"\D", "", phone)
    if digits.startswith("998") and len(digits) == 12:
        return digits  # 9989XXXXXXXX
    if len(digits) == 9 and digits.startswith("9"):  # 9XXXXXXXX
        return "998" + digits
    if len(digits) == 12 and digits.startswith("998"):
        return digits
    return None

async def _login(client: httpx.AsyncClient) -> str:
    global _token_cache
    async with _token_lock:
        # boshqa coroutine lockdan o‘tguncha token olgan bo‘lsa qaytamiz
        if _token_cache.get("access_token"):
            return _token_cache["access_token"]
        resp = await client.post(
            f"{ESKIZ_BASE_URL}/api/auth/login",
            data={"email": ESKIZ_EMAIL, "password": ESKIZ_PASSWORD},
            timeout=20,
        )
        resp.raise_for_status()
        data = resp.json()
        token = data.get("data", {}).get("token") or data.get("data", {}).get("access_token")
        if not token:
            raise RuntimeError("Eskiz token olinmadi")
        _token_cache["access_token"] = token
        return token

async def _get_token(client: httpx.AsyncClient) -> str:
    token = _token_cache.get("access_token")
    if token:
        return token
    return await _login(client)

async def _send_raw_sms(client: httpx.AsyncClient, phone: str, message: str) -> httpx.Response:
    token = await _get_token(client)
    headers = {"Authorization": f"Bearer {token}"}
    payload = {
        "mobile_phone": phone,       # 9989XXXXXXXX
        "message": message,          # matn
        "from": ESKIZ_FROM,          # 4546 yoki tasdiqlangan Sender ID
        "callback_url": "https://example.com/sms/callback"  # ixtiyoriy
    }
    resp = await client.post(
        f"{ESKIZ_BASE_URL}/api/message/sms/send",
        data=payload,
        headers=headers,
        timeout=20,
    )
    return resp

def _is_test_only_error(resp: httpx.Response) -> bool:
    try:
        j = resp.json()
    except Exception:
        return False
    # Eskiz xabari: “Sizning statusda ... faqat Test ...”
    msg = (j.get("message") or j.get("error") or "").lower()
    return "faqat test" in msg or "test uchun" in msg

async def send_sms(phone_raw: str, message: str) -> Dict:
    """
    Telefon raqamini tozalaydi, odatiy xabarni yuborishga urunadi.
    Agar Eskiz test-cheklovi bo‘lsa, fallback qilib “Bu Eskiz dan test” yuboradi.
    """
    phone = _clean_uz_phone(phone_raw)
    if not phone:
        return {"ok": False, "reason": "Telefon raqam noto‘g‘ri", "phone_raw": phone_raw}

    async with httpx.AsyncClient() as client:
        resp = await _send_raw_sms(client, phone, message)
        if resp.status_code == 401:
            # token eskirgan: qayta login qilib urinamiz
            await _login(client)
            resp = await _send_raw_sms(client, phone, message)

        if resp.is_success:
            return {"ok": True, "status_code": resp.status_code, "data": resp.json()}

        # Test statusiga tushib qolsa — fallback
        if _is_test_only_error(resp):
            test_msg = "Bu Eskiz dan test"
            resp2 = await _send_raw_sms(client, phone, test_msg)
            if resp2.status_code == 401:
                await _login(client)
                resp2 = await _send_raw_sms(client, phone, test_msg)
            if resp2.is_success:
                return {
                    "ok": True,
                    "fallback_test": True,
                    "status_code": resp2.status_code,
                    "data": resp2.json(),
                }

        # boshqa xatolar
        out = {"ok": False, "status_code": resp.status_code}
        try:
            out["data"] = resp.json()
        except Exception:
            out["text"] = resp.text
        return out
