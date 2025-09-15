#utils.py
from passlib.context import CryptContext
import random
import string

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def generate_random_password(length=10):
    characters = string.ascii_letters + string.digits + "!@#$%^&*"
    return ''.join(random.choice(characters) for _ in range(length))

def generate_student_password(login: str) -> str:
    """Login asosida o‘xshash, ammo random xavfsiz parol yaratadi"""
    suffix = ''.join(random.choices("!@#$%&*", k=1)) + str(random.randint(100, 999))
    return f"{login.replace('.', '')}{suffix}"
