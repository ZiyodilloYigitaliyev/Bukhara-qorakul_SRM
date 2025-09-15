from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from datetime import datetime
from typing import Optional, List
from app.db.database import get_db
from app.models.payment import Payment, PaymentState

router = APIRouter(prefix="/payments", tags=["Payments"])

@router.get("")
async def list_payments(
    db: AsyncSession = Depends(get_db),
    student_id: Optional[int] = Query(None),
    date_from: Optional[str] = Query(None, description="YYYY-MM-DD"),
    date_to: Optional[str] = Query(None, description="YYYY-MM-DD"),
    state: Optional[int] = Query(None, description="0=CREATED,1=PERFORMED,2=CANCELLED"),
    limit: int = 50,
    offset: int = 0
):
    conds = []
    if student_id is not None:
        conds.append(Payment.student_id == student_id)
    if state is not None:
        conds.append(Payment.state == PaymentState(state))
    if date_from:
        dtf = datetime.fromisoformat(date_from)
        conds.append(Payment.created_at >= dtf)
    if date_to:
        dtt = datetime.fromisoformat(date_to)  # ekskluziv qilsangiz ham bo‘ladi
        conds.append(Payment.created_at <= dtt)

    q = select(Payment).where(and_(*conds)) if conds else select(Payment)
    q = q.order_by(Payment.created_at.desc()).limit(limit).offset(offset)
    rows = (await db.execute(q)).scalars().all()

    # Minimal chiqish — xohlasangiz Pydantic schema qo‘shasiz
    return [
        {
            "id": r.id,
            "student_id": r.student_id,
            "service_id": r.service_id,
            "amount_sum": r.amount_tiyin / 100,
            "currency": r.currency,
            "state": int(r.state),
            "created_at": r.created_at,
            "performed_at": r.performed_at,
            "cancelled_at": r.cancelled_at,
            "paynet_transaction_id": r.paynet_transaction_id,
            "provider_trn_id": r.provider_trn_id,
            "fields": r.fields
        }
        for r in rows
    ]
