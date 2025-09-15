# app/crud/credentials.py
import re, secrets, string, unicodedata
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

def ascii_slug(text: str) -> str:
    # Har xil alfavit va aksentlarni tozalab, [a-z0-9.] formatga keltiramiz
    text = unicodedata.normalize("NFKD", text)
    text = "".join(c for c in text if not unicodedata.combining(c))
    text = text.lower()
    text = re.sub(r"[^a-z0-9]+", ".", text).strip(".")
    return text or "user"

def gen_password(length: int = 12) -> str:
    rng = secrets.SystemRandom()
    # Kamida bitta kichik, bitta katta, bitta raqam bo'lsin
    core = (
        rng.choice(string.ascii_lowercase) +
        rng.choice(string.ascii_uppercase) +
        rng.choice(string.digits)
    )
    alphabet = string.ascii_letters + string.digits
    core += "".join(rng.choice(alphabet) for _ in range(length - len(core)))
    pw = list(core)
    rng.shuffle(pw)
    return "".join(pw)

async def make_unique_login_for_model(
    db: AsyncSession, Model, first_name: str, last_name: str, maxlen: int = 50
) -> str:
    base = ascii_slug(f"{first_name}.{last_name}")[: maxlen - 4]  # suffixlar uchun joy qoldiramiz
    # bo'sh bo'lsa default "user"
    if not base:
        base = "user"
    # agar band bo'lmasa darhol qaytaramiz
    exists = await db.execute(select(Model.id).where(Model.login == base))
    if exists.first() is None:
        return base

    # shu prefiks bilan barchasini olaylik
    res = await db.execute(select(Model.login).where(Model.login.ilike(f"{base}%")))
    taken = set(res.scalars().all())

    for i in range(1, 1000):
        cand = f"{base}{i}"
        if len(cand) > maxlen:
            cand = cand[:maxlen]
        if cand not in taken:
            return cand

    # fallback
    return (base + str(secrets.randbelow(10_000)))[:maxlen]
