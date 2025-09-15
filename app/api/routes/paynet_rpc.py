from fastapi import APIRouter, Request, HTTPException, Depends
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from pydantic import BaseModel
from datetime import datetime, timedelta, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from app.db.database import get_db
from app.models.student import Student
from app.models.payment import Payment, PaymentState

router = APIRouter(prefix="/paynet-rpc", tags=["Paynet JSON-RPC"])
security = HTTPBasic()

USERNAME = "paynet_user"
PASSWORD = "paynet_pass"

class RpcRequest(BaseModel):
    jsonrpc: str
    method: str
    id: int | str
    params: dict

def gmt5_now_str():
    return (datetime.utcnow() + timedelta(hours=5)).strftime("%Y-%m-%d %H:%M:%S")

def ok(id, result): return {"jsonrpc": "2.0", "id": id, "result": result}
def err(id, code, message): return {"jsonrpc": "2.0", "id": id, "error": {"code": code, "message": message}}

async def _find_student_by_client_id(db: AsyncSession, client_id: str) -> Student | None:
    # client_id ni siz “student_code” sifatida yuborasiz deb faraz qildik
    q = await db.execute(select(Student).where(Student.student_code == client_id))
    return q.scalar_one_or_none()

@router.post("")
async def rpc(request: Request, creds: HTTPBasicCredentials = Depends(security), db: AsyncSession = Depends(get_db)):
    if not (creds.username == USERNAME and creds.password == PASSWORD):
        raise HTTPException(status_code=401, detail="Unauthorized")

    body = await request.json()
    rpc_req = RpcRequest(**body)
    if rpc_req.jsonrpc != "2.0":
        return err(rpc_req.id, -32600, "Invalid JSON-RPC version")

    method = rpc_req.method
    p = rpc_req.params or {}
    try:
        if method == "GetInformation":
            fields = p.get("fields", {}) or {}
            client_id = fields.get("client_id")
            student = await _find_student_by_client_id(db, client_id) if client_id else None

            # Bu yerda, masalan, mijoz nomi va hozirgi qarzini qaytarishingiz mumkin
            return ok(rpc_req.id, {
                "status": 0,
                "timestamp": gmt5_now_str(),
                "fields": {
                    "name": f"{student.first_name} {student.last_name}" if student else "Unknown",
                    "client_id": client_id
                }
            })

        elif method == "PerformTransaction":
            # Paynet dan keladigan asosiy paramlar: amount (tiyinda), serviceId, transactionId, fields
            amount = int(p.get("amount", 0))
            service_id = int(p.get("serviceId"))
            paynet_trn_id = int(p.get("transactionId"))
            fields = p.get("fields", {}) or {}
            client_id = fields.get("client_id")

            # O‘quvchini aniqlash
            student = await _find_student_by_client_id(db, client_id) if client_id else None

            # Yangi yozuv (PERFORMED)
            payment = Payment(
                student_id=student.id if student else None,
                service_id=service_id,
                amount_tiyin=amount,
                currency="UZS",
                state=PaymentState.PERFORMED,
                performed_at=datetime.utcnow(),
                paynet_transaction_id=paynet_trn_id,
                fields=fields,
                raw_request=body
            )
            db.add(payment)
            await db.flush()   # payment.id hosil bo‘ladi
            payment.provider_trn_id = payment.id
            await db.commit()

            return ok(rpc_req.id, {
                "timestamp": gmt5_now_str(),
                "providerTrnId": payment.provider_trn_id,
                "fields": fields
            })

        elif method == "CheckTransaction":
            # Paynet transactionId orqali topamiz
            paynet_trn_id = int(p.get("transactionId"))
            q = await db.execute(select(Payment).where(Payment.paynet_transaction_id == paynet_trn_id))
            payment = q.scalar_one_or_none()
            if not payment:
                return ok(rpc_req.id, {
                    "transactionState": 3,  # not found
                    "timestamp": gmt5_now_str()
                })
            state_map = {
                PaymentState.PERFORMED: 1,
                PaymentState.CANCELLED: 2,
                PaymentState.CREATED: 0,
            }
            return ok(rpc_req.id, {
                "transactionState": state_map.get(payment.state, 0),
                "timestamp": gmt5_now_str(),
                "providerTrnId": payment.provider_trn_id
            })

        elif method == "CancelTransaction":
            paynet_trn_id = int(p.get("transactionId"))
            q = await db.execute(select(Payment).where(Payment.paynet_transaction_id == paynet_trn_id))
            payment = q.scalar_one_or_none()
            if not payment:
                # bekor qilinadigan tranzaksiya topilmadi
                return ok(rpc_req.id, {
                    "transactionState": 3,
                    "timestamp": gmt5_now_str()
                })
            payment.state = PaymentState.CANCELLED
            payment.cancelled_at = datetime.utcnow()
            await db.commit()
            return ok(rpc_req.id, {
                "providerTrnId": payment.provider_trn_id,
                "timestamp": gmt5_now_str(),
                "transactionState": 2
            })

        elif method == "GetStatement":
            # bu yerda davr bo‘yicha ro‘yxat qaytarish mantiqini qo‘shasiz (ixtiyoriy)
            return ok(rpc_req.id, {"statements": []})

        else:
            return err(rpc_req.id, -32601, "Method not found")

    except Exception as e:
        # xatoni log qiling (logger), lekin foydalanuvchiga umumiy xabar
        return err(rpc_req.id, -32603, "Internal error")
