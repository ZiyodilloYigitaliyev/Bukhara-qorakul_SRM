from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.db.database import get_db
from app.schemas.auth import LoginRequest, Token, TokenOut
from app.schemas.user import UserCreate, UserOut
from app.models.user import User
from app.core.security import verify_password, get_password_hash, create_access_token
from fastapi.security import OAuth2PasswordRequestForm
from app.core.config import settings



router = APIRouter(prefix="/auth", tags=["Auth"])

@router.post("/register", response_model=UserOut)
async def register(data: UserCreate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.username == data.username))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Username already exists")

    new_user = User(
        full_name=data.full_name,
        username=data.username,
        hashed_password=get_password_hash(data.password),
        role=data.role
    )
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)
    return new_user





@router.post("/login", response_model=TokenOut)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db),
):
    # 1) foydalanuvchini topish (DIQQAT: OAuth2 form 'username' ni yuboradi)
    res = await db.execute(select(User).where(User.username == form_data.username))
    user: User | None = res.scalar_one_or_none()

    # 2) tekshiruvlar
    if not user or not verify_password(form_data.password, user.hashed_password):
        # Atayin umumiy xabar — credential leak bo'lmasin
        raise HTTPException(status_code=401, detail="Incorrect username or password")

    if hasattr(user, "is_active") and not getattr(user, "is_active"):
        raise HTTPException(status_code=403, detail="User is inactive")

    # 3) role qiymatini stringga keltiramiz (Enum.value yoki str)
    role_value = getattr(user.role, "value", user.role)
    if role_value is None:
        role_value = "user"

    # 4) token yaratish
    token = create_access_token(subject=user.id, role=role_value)

    # 5) javob
    return TokenOut(
        access_token=token,
        token_type="bearer",
        role=role_value,
    )