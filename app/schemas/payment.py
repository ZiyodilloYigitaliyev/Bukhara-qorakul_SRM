# app/schemas/payment.py
from datetime import datetime
from typing import Optional, Any
from pydantic import BaseModel, ConfigDict, computed_field
from enum import IntEnum


class PaymentState(IntEnum):
    CREATED   = 0
    PERFORMED = 1
    CANCELLED = 2


class PaymentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    student_id: Optional[int]
    service_id: int
    amount_tiyin: int
    currency: str
    state: PaymentState
    created_at: datetime
    performed_at: Optional[datetime]
    cancelled_at: Optional[datetime]
    paynet_transaction_id: Optional[int]
    provider_trn_id: Optional[int]
    fields: Optional[dict]
    meta: Optional[dict]

    @computed_field
    @property
    def amount_sum(self) -> float:
        # ko‘rsatishda qulay bo‘lsin: tiyinni so‘mga o‘girib beradi
        return self.amount_tiyin / 100
