import os
import asyncio
import argparse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import async_session  
from app.models.user import User
from app.core.utils import hash_password


async def ensure_superuser(username: str, password: str, full_name: str) -> None:
    async with async_session() as session:  
        # username bo'yicha idempotent tekshiruv
        existing: User | None = await session.scalar(
            select(User).where(User.username == username)
        )
        if existing:
            print(f"ℹ️ Superuser allaqachon mavjud: {username}")
            return

        su = User(
            full_name=full_name,
            username=username,
            hashed_password=hash_password(password),
            role="superuser",      # modeldagi qiymatga mos bo'lsin (Enum bo'lsa, Enumdan foydalaning)
            is_active=True
        )
        session.add(su)
        await session.commit()
        print(f"✅ Superuser yaratildi: {username}")


def main():
    parser = argparse.ArgumentParser(description="Create or ensure a superuser exists.")
    parser.add_argument(
        "--username",
        default=os.getenv("SUPERUSER_USERNAME"),
        help="Superuser username (default: env SUPERUSER_USERNAME)"
    )
    parser.add_argument(
        "--password",
        default=os.getenv("SUPERUSER_PASSWORD"),
        help="Superuser password (default: env SUPERUSER_PASSWORD)",
    )
    parser.add_argument(
        "--name",
        default=os.getenv("SUPERUSER_FULL_NAME", "Ziyodillo yigitaliyev"),
        help="Superuser full name (default: env SUPERUSER_FULL_NAME)",
    )
    args = parser.parse_args()

    # Minimal himoya: bo'sh passwordga yo'l qo'ymaymiz
    if not args.password or args.password.strip() == "":
        raise SystemExit("❌ Parol bo'sh bo'lmasligi kerak. --password yoki SUPERUSER_PASSWORD kiriting.")

    asyncio.run(ensure_superuser(args.username, args.password, args.name))


if __name__ == "__main__":
    main()
