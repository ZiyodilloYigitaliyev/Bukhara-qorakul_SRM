import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))
import asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import async_session
from app.models.user import User
from app.core.utils import hash_password


async def create_superuser():
    async with async_session() as session:  
        existing = await session.execute(
            User.__table__.select().where(User.username == "admin")
        )
        result = existing.scalar_one_or_none()
        if result:
            print("Superuser allaqachon mavjud.")
            return

        superuser = User(
            full_name="Ziyodillo yigitaliyev",
            username="admin",
            hashed_password=hash_password("admin"),  # parolni o'zgartiring
            role="superuser",
            is_active=True
        )
        session.add(superuser)
        await session.commit()
        print("✅ Superuser yaratildi.")


if __name__ == "__main__":
    asyncio.run(create_superuser())
