# app/realtime/chat_manager.py
from collections import defaultdict
from typing import Dict, Set, Tuple, Optional
from fastapi import WebSocket
from jose import jwt, JWTError
from app.core.config import settings  # SECRET_KEY, ALGORITHM

def user_key(role: str, uid: int) -> str:
    return f"{role}:{uid}"

class ChatConnectionManager:
    def __init__(self):
        self.rooms: Dict[str, Set[WebSocket]] = defaultdict(set)  # room_slug -> sockets
        self.users: Dict[str, Set[WebSocket]] = defaultdict(set)  # "teacher:12" -> sockets

    async def accept(self, ws: WebSocket):
        await ws.accept()

    def join_room(self, room_slug: str, ws: WebSocket):
        self.rooms[room_slug].add(ws)

    def leave_room(self, room_slug: str, ws: WebSocket):
        self.rooms[room_slug].discard(ws)

    def bind_user(self, ukey: str, ws: WebSocket):
        self.users[ukey].add(ws)

    def unbind_user(self, ukey: str, ws: WebSocket):
        self.users[ukey].discard(ws)

    async def broadcast_room(self, room_slug: str, payload: dict):
        dead = []
        for ws in list(self.rooms.get(room_slug, set())):
            try:
                await ws.send_json(payload)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.leave_room(room_slug, ws)

manager = ChatConnectionManager()

def verify_mobile_token(token: Optional[str]) -> Tuple[Optional[int], Optional[str]]:
    """
    JWT talablari:
      sub -> user_id (int)
      role -> 'teacher' | 'student'
      aud  -> 'mobile' (faqat mobile ilovaga ruxsat beramiz)
    """
    if not token:
        return None, None
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        if payload.get("aud") != "mobile":
            return None, None
        return int(payload.get("sub")), payload.get("role")
    except (JWTError, ValueError):
        return None, None
