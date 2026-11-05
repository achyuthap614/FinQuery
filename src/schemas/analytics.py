"""Pydantic schemas for Financial Analytics results."""
from typing import List, Dict, Optional
from pydantic import BaseModel, Field

class FinancialSummary(BaseModel):
    total_income: float = Field(..., description="Sum of all income transactions")
    total_expenses: float = Field(..., description="Sum of all expense transactions")
    net_balance: float = Field(..., description="Net balance = Total income - Total expenses")
    savings_rate_percent: float = Field(..., description="Savings rate as percentage of income")
    total_transactions: int = Field(..., description="Total number of transactions analyzed")
    date_range_start: Optional[str] = None
    date_range_end: Optional[str] = None

class CategorySpendingItem(BaseModel):
    category: str
    total_amount: float
    transaction_count: int
    percentage_of_total: float

class MonthlySpendingItem(BaseModel):
    month: str  # YYYY-MM
    income: float
    expenses: float
    net: float
    transaction_count: int

class CategoryDelta(BaseModel):
    category: str
    month1_amount: float
    month2_amount: float
    difference: float
    percentage_change: Optional[float] = None

class MonthlyComparisonResult(BaseModel):
    month1: str
    month2: str
    month1_expenses: float
    month2_expenses: float
    expense_difference: float
    expense_percentage_change: Optional[float] = None
    month1_income: float
    month2_income: float
    income_difference: float
    category_breakdown: List[CategoryDelta]

class UnusualSpendingItem(BaseModel):
    transaction_id: int
    date: str
    category: str
    description: str
    amount: float
    category_average: float
    category_std_dev: float
    z_score: float
    deviation_factor: float
    reason: str

class UnusualSpendingResponse(BaseModel):
    method: str = "Descriptive Statistics (Z-Score and Historical Category Standard Deviation)"
    threshold_z: float
    total_anomalies_found: int
    anomalies: List[UnusualSpendingItem]
