# app/models/payment.py
from enum import IntEnum
from datetime import datetime
from sqlalchemy import (
    Column, Integer, BigInteger, String, DateTime, ForeignKey, JSON, Enum, func
)
from sqlalchemy.orm import relationship
from app.db.base import Base


class PaymentState(IntEnum):
    CREATED   = 0   # yozildi, lekin hali perform bo‘lmagan
    PERFORMED = 1   # muvaffaqiyatli yakunlangan (PerformTransaction)
    CANCELLED = 2   # bekor qilingan (CancelTransaction)


class Payment(Base):
    __tablename__ = "payments"

    id = Column(Integer, primary_key=True, index=True)

    # Kim to‘ladi?
    student_id = Column(Integer, ForeignKey("students.id", ondelete="SET NULL"), index=True, nullable=True)
    student = relationship("Student", back_populates="payments", lazy="joined")

    # Paynet rekvizitlari
    service_id = Column(Integer, index=True, nullable=False)
    paynet_transaction_id = Column(BigInteger, index=True, nullable=True)   # Paynet "transactionId"
    provider_trn_id = Column(BigInteger, index=True, nullable=True)         # Siz qaytaradigan "providerTrnId" (ko‘pincha payment.id)

    amount_tiyin = Column(BigInteger, nullable=False)  # tiyinda saqlaymiz
    currency = Column(String(8), default="UZS")

    state = Column(Enum(PaymentState), default=PaymentState.CREATED, nullable=False)

    # vaqtlar
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    performed_at = Column(DateTime, nullable=True)
    cancelled_at = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)

    # audit
    fields = Column(JSON, nullable=True)         # Paynet "fields" (masalan, {"client_id": "..."} )
    meta = Column(JSON, nullable=True)           # qo‘shimcha ma’lumotlar (device/platform va h.k.)
    raw_request = Column(JSON, nullable=True)    # RPC kelgan xom so‘rov (ixtiyoriy)
    raw_response = Column(JSON, nullable=True)   # RPC qaytgan xom javob (ixtiyoriy)
