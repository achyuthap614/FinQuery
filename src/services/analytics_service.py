"""Financial analytics and statistical calculation service."""
import math
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func
from src.database.models import Transaction
from src.schemas.analytics import (
    FinancialSummary,
    CategorySpendingItem,
    MonthlySpendingItem,
    MonthlyComparisonResult,
    CategoryDelta,
    UnusualSpendingResponse,
    UnusualSpendingItem
)
from src.utils.logger import logger

class AnalyticsService:
    @staticmethod
    def get_financial_summary(
        db: Session,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> FinancialSummary:
        """Computes total income, total expenses, net balance, and savings rate."""
        query = db.query(Transaction)
        if start_date:
            query = query.filter(Transaction.date >= start_date)
        if end_date:
            query = query.filter(Transaction.date <= end_date)

        total_transactions = query.count()

        # Compute total income
        income_query = query.filter(Transaction.transaction_type == "income")
        total_income = income_query.with_entities(func.coalesce(func.sum(Transaction.amount), 0.0)).scalar() or 0.0

        # Compute total expenses
        expense_query = query.filter(Transaction.transaction_type == "expense")
        total_expenses = expense_query.with_entities(func.coalesce(func.sum(Transaction.amount), 0.0)).scalar() or 0.0

        net_balance = total_income - total_expenses
        savings_rate = (net_balance / total_income * 100.0) if total_income > 0 else 0.0

        return FinancialSummary(
            total_income=round(total_income, 2),
            total_expenses=round(total_expenses, 2),
            net_balance=round(net_balance, 2),
            savings_rate_percent=round(savings_rate, 2),
            total_transactions=total_transactions,
            date_range_start=start_date,
            date_range_end=end_date
        )

    @staticmethod
    def get_category_spending(
        db: Session,
        category: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        transaction_type: str = "expense"
    ) -> List[CategorySpendingItem]:
        """Calculates spending breakdown grouped by category."""
        query = db.query(Transaction).filter(Transaction.transaction_type == transaction_type.lower())

        if category:
            query = query.filter(Transaction.category.ilike(f"%{category.strip()}%"))
        if start_date:
            query = query.filter(Transaction.date >= start_date)
        if end_date:
            query = query.filter(Transaction.date <= end_date)

        # Get total amount for percentage calculation
        total_amount = query.with_entities(func.coalesce(func.sum(Transaction.amount), 0.0)).scalar() or 0.0

        results = (
            query.with_entities(
                Transaction.category,
                func.sum(Transaction.amount).label("cat_total"),
                func.count(Transaction.id).label("cat_count")
            )
            .group_by(Transaction.category)
            .order_by(func.sum(Transaction.amount).desc())
            .all()
        )

        items = []
        for cat_name, cat_tot, cat_cnt in results:
            cat_tot_val = round(float(cat_tot), 2)
            pct = round((cat_tot_val / total_amount * 100.0), 2) if total_amount > 0 else 0.0
            items.append(CategorySpendingItem(
                category=cat_name,
                total_amount=cat_tot_val,
                transaction_count=cat_cnt,
                percentage_of_total=pct
            ))

        return items

    @staticmethod
    def get_monthly_spending(db: Session, limit_months: int = 24) -> List[MonthlySpendingItem]:
        """Calculates monthly income, expenses, and net balance."""
        # Using SQLite substr(date, 1, 7) for 'YYYY-MM'
        month_expr = func.substr(Transaction.date, 1, 7).label("month")

        months_raw = (
            db.query(month_expr)
            .distinct()
            .order_by(month_expr.asc())
            .all()
        )

        all_months = [m[0] for m in months_raw if m[0]]
        if len(all_months) > limit_months:
            all_months = all_months[-limit_months:]

        monthly_items = []
        for m in all_months:
            m_query = db.query(Transaction).filter(func.substr(Transaction.date, 1, 7) == m)
            m_income = m_query.filter(Transaction.transaction_type == "income").with_entities(
                func.coalesce(func.sum(Transaction.amount), 0.0)
            ).scalar() or 0.0
            m_expenses = m_query.filter(Transaction.transaction_type == "expense").with_entities(
                func.coalesce(func.sum(Transaction.amount), 0.0)
            ).scalar() or 0.0
            cnt = m_query.count()

            monthly_items.append(MonthlySpendingItem(
                month=m,
                income=round(float(m_income), 2),
                expenses=round(float(m_expenses), 2),
                net=round(float(m_income) - float(m_expenses), 2),
                transaction_count=cnt
            ))

        return monthly_items

    @staticmethod
    def get_largest_transactions(
        db: Session,
        limit: int = 5,
        transaction_type: str = "expense",
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Returns the largest transactions sorted by amount descending."""
        query = db.query(Transaction).filter(Transaction.transaction_type == transaction_type.lower())

        if start_date:
            query = query.filter(Transaction.date >= start_date)
        if end_date:
            query = query.filter(Transaction.date <= end_date)

        records = query.order_by(Transaction.amount.desc()).limit(limit).all()
        return [t.to_dict() for t in records]

    @classmethod
    def compare_monthly_spending(
        cls,
        db: Session,
        month1: str,
        month2: str
    ) -> MonthlyComparisonResult:
        """Compares spending and income between two specific months (YYYY-MM)."""
        month1 = month1.strip()
        month2 = month2.strip()

        # Month 1 totals
        q1 = db.query(Transaction).filter(func.substr(Transaction.date, 1, 7) == month1)
        m1_expenses = q1.filter(Transaction.transaction_type == "expense").with_entities(
            func.coalesce(func.sum(Transaction.amount), 0.0)
        ).scalar() or 0.0
        m1_income = q1.filter(Transaction.transaction_type == "income").with_entities(
            func.coalesce(func.sum(Transaction.amount), 0.0)
        ).scalar() or 0.0

        # Month 2 totals
        q2 = db.query(Transaction).filter(func.substr(Transaction.date, 1, 7) == month2)
        m2_expenses = q2.filter(Transaction.transaction_type == "expense").with_entities(
            func.coalesce(func.sum(Transaction.amount), 0.0)
        ).scalar() or 0.0
        m2_income = q2.filter(Transaction.transaction_type == "income").with_entities(
            func.coalesce(func.sum(Transaction.amount), 0.0)
        ).scalar() or 0.0

        exp_diff = m2_expenses - m1_expenses
        exp_pct_change = round((exp_diff / m1_expenses * 100.0), 2) if m1_expenses > 0 else None

        inc_diff = m2_income - m1_income

        # Category by category comparison
        cats1 = dict(
            q1.filter(Transaction.transaction_type == "expense")
            .with_entities(Transaction.category, func.sum(Transaction.amount))
            .group_by(Transaction.category)
            .all()
        )
        cats2 = dict(
            q2.filter(Transaction.transaction_type == "expense")
            .with_entities(Transaction.category, func.sum(Transaction.amount))
            .group_by(Transaction.category)
            .all()
        )

        all_categories = sorted(set(list(cats1.keys()) + list(cats2.keys())))
        cat_deltas = []
        for cat in all_categories:
            amt1 = round(float(cats1.get(cat, 0.0)), 2)
            amt2 = round(float(cats2.get(cat, 0.0)), 2)
            diff = round(amt2 - amt1, 2)
            pct = round((diff / amt1 * 100.0), 2) if amt1 > 0 else None
            cat_deltas.append(CategoryDelta(
                category=cat,
                month1_amount=amt1,
                month2_amount=amt2,
                difference=diff,
                percentage_change=pct
            ))

        return MonthlyComparisonResult(
            month1=month1,
            month2=month2,
            month1_expenses=round(m1_expenses, 2),
            month2_expenses=round(m2_expenses, 2),
            expense_difference=round(exp_diff, 2),
            expense_percentage_change=exp_pct_change,
            month1_income=round(m1_income, 2),
            month2_income=round(m2_income, 2),
            income_difference=round(inc_diff, 2),
            category_breakdown=cat_deltas
        )

    @classmethod
    def get_average_monthly_spending(cls, db: Session) -> Dict[str, float]:
        """Calculates average monthly expenses and income across all recorded months."""
        monthly_items = cls.get_monthly_spending(db)
        if not monthly_items:
            return {"average_monthly_income": 0.0, "average_monthly_expenses": 0.0, "months_recorded": 0}

        num_months = len(monthly_items)
        tot_inc = sum(m.income for m in monthly_items)
        tot_exp = sum(m.expenses for m in monthly_items)

        return {
            "average_monthly_income": round(tot_inc / num_months, 2),
            "average_monthly_expenses": round(tot_exp / num_months, 2),
            "months_recorded": num_months
        }

    @staticmethod
    def get_unusual_spending(db: Session, threshold_z: float = 2.0) -> UnusualSpendingResponse:
        """
        Detects unusual transactions using statistical Z-Score per category.
        Calculates category sample mean and standard deviation.
        A transaction is flagged if Z-Score >= threshold_z (default 2.0 standard deviations).
        Transparent statistical method, not opaque ML.
        """
        # Fetch all expense transactions
        expenses = db.query(Transaction).filter(Transaction.transaction_type == "expense").all()

        # Group by category
        cat_transactions: Dict[str, List[Transaction]] = {}
        for t in expenses:
            cat_transactions.setdefault(t.category, []).append(t)

        anomalies: List[UnusualSpendingItem] = []

        for category, trans_list in cat_transactions.items():
            if len(trans_list) < 3:
                # Need at least 3 transactions to calculate meaningful sample deviation
                continue

            amounts = [t.amount for t in trans_list]
            mean_val = sum(amounts) / len(amounts)
            variance = sum((x - mean_val) ** 2 for x in amounts) / (len(amounts) - 1)
            std_dev = math.sqrt(variance)

            if std_dev == 0.0:
                continue

            for t in trans_list:
                z = (t.amount - mean_val) / std_dev
                if z >= threshold_z:
                    deviation_factor = round(t.amount / mean_val, 2) if mean_val > 0 else 0.0
                    anomalies.append(UnusualSpendingItem(
                        transaction_id=t.id,
                        date=t.date,
                        category=t.category,
                        description=t.description,
                        amount=round(t.amount, 2),
                        category_average=round(mean_val, 2),
                        category_std_dev=round(std_dev, 2),
                        z_score=round(z, 2),
                        deviation_factor=deviation_factor,
                        reason=f"${t.amount:.2f} is {deviation_factor}x the category average (${mean_val:.2f}) with Z-score {z:.2f} (>{threshold_z} std dev)"
                    ))

        # Sort anomalies by z_score descending
        anomalies.sort(key=lambda x: x.z_score, reverse=True)

        return UnusualSpendingResponse(
            threshold_z=threshold_z,
            total_anomalies_found=len(anomalies),
            anomalies=anomalies
        )
