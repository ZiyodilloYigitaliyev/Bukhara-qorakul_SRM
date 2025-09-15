# app/realtime/chat_ws.py
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, insert
from datetime import datetime
from app.db.database import get_db
from app.models.chat import ChatRoom, ChatMessage
from app.realtime.chat_manager import manager, verify_mobile_token, user_key

router = APIRouter()

async def ensure_room(db: AsyncSession, room_slug: str):
    res = await db.execute(select(ChatRoom).where(ChatRoom.slug == room_slug))
    room = res.scalar_one_or_none()
    if not room:
        await db.execute(insert(ChatRoom).values(slug=room_slug, is_group=False))
        await db.commit()

@router.websocket("/ws/chat/{room_slug}")
async def ws_chat(websocket: WebSocket, room_slug: str, db: AsyncSession = Depends(get_db)):
    # ?token=<MOBILE_JWT>
    token = websocket.query_params.get("token")
    uid, role = verify_mobile_token(token)
    if not uid or role not in ("teacher", "student"):
        await websocket.close(code=4403)  # Forbidden (faqat mobile + teacher/student)
        return

    await manager.accept(websocket)
    manager.join_room(room_slug, websocket)
    manager.bind_user(user_key(role, uid), websocket)
    await ensure_room(db, room_slug)

    try:
        while True:
            incoming = await websocket.receive_json()
            itype = incoming.get("type")

            if itype == "send":
                text = (incoming.get("text") or "").strip()
                mtype = incoming.get("message_type", "text")
                client_msg_id = incoming.get("client_msg_id")

                if not text and mtype == "text":
                    await websocket.send_json({"type": "error", "reason": "empty_text"})
                    continue

                # DB ga yozish (dedupe client_msg_id)
                stmt = insert(ChatMessage).values(
                    room_slug=room_slug,
                    sender_role=role,
                    sender_id=uid,
                    message_type=mtype,
                    text=text,
                    client_msg_id=client_msg_id,
                    delivered=False
                ).returning(ChatMessage.id, ChatMessage.created_at)
                try:
                    res = await db.execute(stmt)
                    row = res.first()
                    await db.commit()
                    msg_id, created_at = row[0], row[1]
                except Exception:
                    await db.rollback()
                    await websocket.send_json({"type": "ack", "status": "duplicate", "client_msg_id": client_msg_id})
                    continue

                # ACK
                await websocket.send_json({
                    "type": "ack",
                    "status": "stored",
                    "message_id": msg_id,
                    "client_msg_id": client_msg_id,
                    "created_at": created_at.isoformat()
                })

                # Broadcast
                await manager.broadcast_room(room_slug, {
                    "type": "message",
                    "message": {
                        "id": msg_id,
                        "room_slug": room_slug,
                        "sender_role": role,
                        "sender_id": uid,
                        "message_type": mtype,
                        "text": text,
                        "delivered": True,
                        "read_at": None,
                        "created_at": created_at.isoformat()
                    }
                })

                # delivered=true
                await db.execute(
                    ChatMessage.__table__.update()
                    .where(ChatMessage.id == msg_id)
                    .values(delivered=True)
                )
                await db.commit()

            elif itype == "typing":
                await manager.broadcast_room(room_slug, {
                    "type": "typing",
                    "from": {"role": role, "id": uid},
                    "room_slug": room_slug
                })

            elif itype == "seen":
                last_id = incoming.get("last_message_id")
                if last_id:
                    now = datetime.utcnow()
                    await db.execute(
                        ChatMessage.__table__.update()
                        .where(ChatMessage.room_slug == room_slug)
                        .where(ChatMessage.id <= last_id)
                        .values(read_at=now)
                    )
                    await db.commit()
                    await manager.broadcast_room(room_slug, {
                        "type": "seen",
                        "by": {"role": role, "id": uid},
                        "room_slug": room_slug,
                        "last_message_id": last_id,
                        "read_at": now.isoformat() + "Z"
                    })
            else:
                await websocket.send_json({"type": "error", "reason": "unknown_type"})
    except WebSocketDisconnect:
        manager.leave_room(room_slug, websocket)
        manager.unbind_user(user_key(role, uid), websocket)
