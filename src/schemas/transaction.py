"""Pydantic schemas for Transaction models."""
from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, ConfigDict, field_validator
import re

class TransactionBase(BaseModel):
    date: str = Field(..., description="Date of transaction in YYYY-MM-DD format", json_schema_extra={"example": "2026-08-15"})
    amount: float = Field(..., gt=0, description="Transaction monetary value strictly greater than 0", json_schema_extra={"example": 120.50})
    category: str = Field(..., min_length=2, max_length=50, description="Financial category", json_schema_extra={"example": "Groceries"})
    description: str = Field(..., min_length=2, max_length=255, description="Transaction details/payee", json_schema_extra={"example": "Supermarket Weekly"})
    transaction_type: str = Field(..., description="Income or expense classification", json_schema_extra={"example": "expense"})
    payment_method: Optional[str] = Field("Bank Transfer", description="Payment instrument")
    account: Optional[str] = Field("Primary Account", description="Bank/wallet account")

    @field_validator("date")
    @classmethod
    def validate_date_format(cls, v: str) -> str:
        pattern = r"^\d{4}-\d{2}-\d{2}$"
        if not re.match(pattern, v.strip()):
            raise ValueError("Date must strictly follow YYYY-MM-DD format")
        return v.strip()

    @field_validator("transaction_type")
    @classmethod
    def validate_transaction_type(cls, v: str) -> str:
        lowered = v.strip().lower()
        if lowered not in ("income", "expense"):
            raise ValueError("transaction_type must be either 'income' or 'expense'")
        return lowered

    @field_validator("category", "description")
    @classmethod
    def clean_text_fields(cls, v: str) -> str:
        return v.strip()

class TransactionCreate(TransactionBase):
    pass

class TransactionRead(TransactionBase):
    id: int
    fingerprint: str
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)

class TransactionFilterParams(BaseModel):
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    category: Optional[str] = None
    transaction_type: Optional[str] = None
    min_amount: Optional[float] = None
    max_amount: Optional[float] = None
    search_query: Optional[str] = None
    limit: int = Field(50, ge=1, le=500)
    offset: int = Field(0, ge=0)

class TransactionUploadSummary(BaseModel):
    total_processed: int
    inserted_count: int
    duplicate_count: int
    invalid_count: int
    errors: List[Dict[str, Any]] = []

class TransactionListResponse(BaseModel):
    total: int
    limit: int
    offset: int
    transactions: List[TransactionRead]
