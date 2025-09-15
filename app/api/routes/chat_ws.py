# app/api/routes/chat_ws.py
from __future__ import annotations
from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect, Query, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from jose import jwt, JWTError
from typing import Dict, Set
from app.db.database import get_db  # sizdagi get_db ni import qiling
from app.core.config import settings
from app.models.student import Student
from app.models.teacher import Teacher
from app.models.chat import SenderType
from app.services.chat_service import (
    get_or_create_room, list_rooms_for_student, list_rooms_for_teacher,
    list_messages, save_message, mark_room_read
)
from app.schemas.chat import ChatRoomOut, ChatMessageOut, ChatRoomCreate, ChatMessageCreate

router = APIRouter(prefix="/chat", tags=["Chat"])

# --- Auth helpers for WS ---
async def get_student_by_token(token: str, db: AsyncSession) -> Student | None:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        sub = payload.get("sub")
        role = payload.get("role") or payload.get("scope")
        if not sub:
            return None
        if role and role != "student":
            return None
        q = await db.execute(
            # agar login email orqali bo'lsa, mos ravishda qidirishni moslang
            # biz id saqlangan deb faraz qilamiz
            # agar sub = user_id bo'lsa:
            # select(Student).where(Student.id == int(sub))
            # ko'p loyihada sub = login bo'ladi; kerak bo'lsa moslang
            # bu yerda id deb faraz qilamiz:
            Student.__table__.select().where(Student.id == int(sub))
        )
        row = q.first()
        if not row:
            return None
        # ORM ob'ektini olish
        s = await db.get(Student, int(sub))
        return s
    except Exception:
        return None

async def get_teacher_by_token(token: str, db: AsyncSession) -> Teacher | None:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        sub = payload.get("sub")
        role = payload.get("role") or payload.get("scope")
        if not sub:
            return None
        if role and role != "teacher":
            return None
        t = await db.get(Teacher, int(sub))
        return t
    except Exception:
        return None

# --- In-memory connections manager ---
class ConnectionManager:
    def __init__(self) -> None:
        self.rooms: Dict[int, Set[WebSocket]] = {}

    async def connect(self, room_id: int, websocket: WebSocket):
        await websocket.accept()
        self.rooms.setdefault(room_id, set()).add(websocket)

    def disconnect(self, room_id: int, websocket: WebSocket):
        try:
            self.rooms[room_id].discard(websocket)
            if not self.rooms[room_id]:
                self.rooms.pop(room_id, None)
        except KeyError:
            pass

    async def broadcast(self, room_id: int, data: dict):
        for ws in list(self.rooms.get(room_id, set())):
            await ws.send_json(data)

manager = ConnectionManager()

# --------- HTTP (Student) ----------
@router.post("/rooms", response_model=ChatRoomOut)
async def create_room(data: ChatRoomCreate, db: AsyncSession = Depends(get_db)):
    room = await get_or_create_room(db, data.student_id, data.teacher_id)
    await db.commit()
    await db.refresh(room)
    return room

@router.get("/student/rooms/my", response_model=list[ChatRoomOut], tags=["Mobile - Student"])
async def my_rooms_student(token: str = Query(..., description="Bearer token (student)"),
                           db: AsyncSession = Depends(get_db)):
    student = await get_student_by_token(token, db)
    if not student:
        raise HTTPException(status_code=401, detail="Unauthorized")
    rooms = await list_rooms_for_student(db, student.id)
    return rooms

@router.get("/teacher/rooms/my", response_model=list[ChatRoomOut], tags=["Teacher"])
async def my_rooms_teacher(token: str = Query(..., description="Bearer token (teacher)"),
                           db: AsyncSession = Depends(get_db)):
    teacher = await get_teacher_by_token(token, db)
    if not teacher:
        raise HTTPException(status_code=401, detail="Unauthorized")
    rooms = await list_rooms_for_teacher(db, teacher.id)
    return rooms

@router.get("/rooms/{room_id}/messages", response_model=list[ChatMessageOut])
async def get_messages(room_id: int, limit: int = 50, before_id: int | None = None,
                       db: AsyncSession = Depends(get_db)):
    msgs = await list_messages(db, room_id, limit=limit, before_id=before_id)
    return msgs

# --------- WebSocket ----------
@router.websocket("/ws/{room_id}")
async def ws_chat(websocket: WebSocket,
                  room_id: int,
                  role: str,                             # "student" yoki "teacher"
                  token: str,
                  db: AsyncSession = Depends(get_db)):
    # Auth
    current_student = None
    current_teacher = None
    if role == "student":
        current_student = await get_student_by_token(token, db)
    elif role == "teacher":
        current_teacher = await get_teacher_by_token(token, db)
    else:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    if not (current_student or current_teacher):
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    await manager.connect(room_id, websocket)
    try:
        while True:
            data = await websocket.receive_json()
            # expected: {"type":"message"|"read", "text": "..."}
            msg_type = data.get("type")
            if msg_type == "message":
                text = (data.get("text") or "").strip()
                if not text:
                    continue
                if current_student:
                    msg = await save_message(db, room_id, SenderType.student, current_student.id, text)
                else:
                    msg = await save_message(db, room_id, SenderType.teacher, current_teacher.id, text)
                await db.commit()
                await db.refresh(msg)
                # Broadcast yangilanish
                await manager.broadcast(room_id, {
                    "event": "message",
                    "payload": {
                        "id": msg.id,
                        "room_id": room_id,
                        "sender_type": msg.sender_type,
                        "sender_id": msg.sender_id,
                        "text": msg.text,
                        "created_at": str(msg.created_at),
                    }
                })
            elif msg_type == "read":
                who = SenderType.student if current_student else SenderType.teacher
                await mark_room_read(db, room_id, who)
                await db.commit()
                await manager.broadcast(room_id, {"event": "read", "by": who.value})
            else:
                # no-op / unknown
                pass
    except WebSocketDisconnect:
        manager.disconnect(room_id, websocket)
