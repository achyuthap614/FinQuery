"""Tests for Financial Analytics calculations."""
import pytest
from src.services.analytics_service import AnalyticsService

def test_financial_summary_calculations(populated_db):
    summary = AnalyticsService.get_financial_summary(populated_db)

    expected_income = 5000.00
    expected_expenses = 1500.00 + 120.50 + 45.00 + 80.00 + 150.00 + 600.00  # 2495.50
    expected_net = expected_income - expected_expenses
    expected_savings_rate = (expected_net / expected_income) * 100.0

    assert summary.total_income == pytest.approx(expected_income, 0.01)
    assert summary.total_expenses == pytest.approx(expected_expenses, 0.01)
    assert summary.net_balance == pytest.approx(expected_net, 0.01)
    assert summary.savings_rate_percent == pytest.approx(expected_savings_rate, 0.01)
    assert summary.total_transactions == 7

def test_category_spending_breakdown(populated_db):
    breakdown = AnalyticsService.get_category_spending(populated_db)
    assert len(breakdown) > 0

    # Rent should be the highest expense category ($1500)
    highest = breakdown[0]
    assert highest.category == "Rent"
    assert highest.total_amount == 1500.00
    assert highest.percentage_of_total > 50.0

    # Total percentages should sum to approximately 100%
    total_pct = sum(item.percentage_of_total for item in breakdown)
    assert total_pct == pytest.approx(100.0, 0.1)

def test_largest_transactions(populated_db):
    largest = AnalyticsService.get_largest_transactions(populated_db, limit=3, transaction_type="expense")
    assert len(largest) == 3
    assert largest[0]["amount"] == 1500.00  # Rent
    assert largest[1]["amount"] == 600.00   # VIP Banquet
    assert largest[2]["amount"] == 150.00   # Weekly Groceries

def test_monthly_spending(populated_db):
    monthly = AnalyticsService.get_monthly_spending(populated_db)
    assert len(monthly) == 1
    assert monthly[0].month == "2026-08"
    assert monthly[0].income == 5000.00
    assert monthly[0].expenses == pytest.approx(2495.50, 0.01)

def test_unusual_spending_detection(populated_db):
    # Add a few more dining transactions to test statistical Z-score
    from src.database.models import Transaction
    for amt, desc in [(40.0, "Lunch 1"), (42.0, "Lunch 2"), (38.0, "Lunch 3")]:
        fp = Transaction.generate_fingerprint("2026-08-25", amt, "Dining", desc, "expense")
        t = Transaction(
            date="2026-08-25",
            amount=amt,
            category="Dining",
            description=desc,
            transaction_type="expense",
            payment_method="Card",
            account="Checking",
            fingerprint=fp
        )
        populated_db.add(t)
    populated_db.commit()

    # Now dining has: 45, 600 (banquet), 40, 42, 38. The 600 banquet is an extreme outlier!
    unusual = AnalyticsService.get_unusual_spending(populated_db, threshold_z=1.5)
    assert unusual.total_anomalies_found >= 1
    top_anomaly = unusual.anomalies[0]
    assert top_anomaly.category == "Dining"
    assert top_anomaly.amount == 600.00
    assert top_anomaly.z_score > 1.5
