"""Financial analytics API routes."""
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from src.api.dependencies import get_db
from src.services.analytics_service import AnalyticsService
from src.schemas.analytics import (
    FinancialSummary,
    CategorySpendingItem,
    MonthlySpendingItem,
    MonthlyComparisonResult,
    UnusualSpendingResponse
)

router = APIRouter(prefix="/analytics", tags=["Financial Analytics"])

@router.get("/summary", response_model=FinancialSummary, summary="Get overall financial summary")
def get_financial_summary(
    start_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD)"),
    db: Session = Depends(get_db)
):
    """Calculates total income, total expenses, net balance, and savings rate."""
    return AnalyticsService.get_financial_summary(db, start_date=start_date, end_date=end_date)

@router.get("/categories", response_model=List[CategorySpendingItem], summary="Get spending breakdown by category")
def get_category_analytics(
    category: Optional[str] = Query(None, description="Filter specific category"),
    start_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD)"),
    transaction_type: str = Query("expense", description="'expense' or 'income'"),
    db: Session = Depends(get_db)
):
    """Calculates total spent and percentage contribution per category."""
    return AnalyticsService.get_category_spending(
        db,
        category=category,
        start_date=start_date,
        end_date=end_date,
        transaction_type=transaction_type
    )

@router.get("/monthly", response_model=List[MonthlySpendingItem], summary="Get monthly spending and income trends")
def get_monthly_trends(
    limit_months: int = Query(24, ge=1, le=60, description="Max months to return"),
    db: Session = Depends(get_db)
):
    """Calculates income, expenses, and net balance grouped by month (YYYY-MM)."""
    return AnalyticsService.get_monthly_spending(db, limit_months=limit_months)

@router.get("/largest", response_model=List[Dict[str, Any]], summary="Get largest transactions")
def get_largest_transactions(
    limit: int = Query(5, ge=1, le=50, description="Number of transactions"),
    transaction_type: str = Query("expense", description="'expense' or 'income'"),
    start_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD)"),
    db: Session = Depends(get_db)
):
    """Returns top N transactions ordered by value descending."""
    return AnalyticsService.get_largest_transactions(
        db,
        limit=limit,
        transaction_type=transaction_type,
        start_date=start_date,
        end_date=end_date
    )

@router.get("/compare", response_model=MonthlyComparisonResult, summary="Compare spending between two months")
def compare_months(
    month1: str = Query(..., description="First month in YYYY-MM format, e.g. '2026-07'"),
    month2: str = Query(..., description="Second month in YYYY-MM format, e.g. '2026-08'"),
    db: Session = Depends(get_db)
):
    """Compares total expenses, income, and category shifts between two months."""
    return AnalyticsService.compare_monthly_spending(db, month1=month1, month2=month2)

@router.get("/unusual", response_model=UnusualSpendingResponse, summary="Detect unusual spending anomalies")
def detect_unusual_spending(
    threshold_z: float = Query(2.0, ge=1.0, le=5.0, description="Standard deviation Z-score threshold"),
    db: Session = Depends(get_db)
):
    """
    Flags unusual transactions using category-level statistical Z-score
    against historical standard deviation.
    """
    return AnalyticsService.get_unusual_spending(db, threshold_z=threshold_z)

@router.get("/averages", summary="Get average monthly income and expenses")
def get_average_monthly(db: Session = Depends(get_db)):
    """Computes mean monthly expenses and income across all recorded months."""
    return AnalyticsService.get_average_monthly_spending(db)
