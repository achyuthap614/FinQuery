"""Tests for Transaction Service, validation, and deduplication."""
import pytest
from src.services.transaction_service import TransactionService
from src.schemas.transaction import TransactionCreate, TransactionFilterParams

def test_normalize_date():
    assert TransactionService.normalize_date("2026-08-15") == "2026-08-15"
    assert TransactionService.normalize_date("15-08-2026") == "2026-08-15"
    assert TransactionService.normalize_date("08/15/2026") == "2026-08-15"
    assert TransactionService.normalize_date("2026/08/15") == "2026-08-15"

    with pytest.raises(ValueError):
        TransactionService.normalize_date("invalid-date-string")

def test_parse_amount():
    assert TransactionService.parse_amount(150) == 150.0
    assert TransactionService.parse_amount(" $250.75 ") == 250.75
    assert TransactionService.parse_amount("1,250.00") == 1250.0

    with pytest.raises(ValueError):
        TransactionService.parse_amount(-50.0)

    with pytest.raises(ValueError):
        TransactionService.parse_amount("not_a_number")

def test_import_valid_csv(db_session, sample_csv_data):
    summary = TransactionService.import_csv(db_session, sample_csv_data)
    assert summary.inserted_count == 7
    assert summary.duplicate_count == 0
    assert summary.invalid_count == 0

def test_duplicate_detection(db_session, sample_csv_data):
    # First import
    summary1 = TransactionService.import_csv(db_session, sample_csv_data)
    assert summary1.inserted_count == 7

    # Second import with identical data
    summary2 = TransactionService.import_csv(db_session, sample_csv_data)
    assert summary2.inserted_count == 0
    assert summary2.duplicate_count == 7

def test_invalid_records_handling(db_session):
    bad_csv = """date,amount,category,description,transaction_type
2026-08-01,500.00,Groceries,Valid Row,expense
not-a-date,100.00,Dining,Bad Date,expense
2026-08-03,-45.00,Utilities,Negative Amount,expense
2026-08-04,75.00,,Missing Category,expense
"""
    summary = TransactionService.import_csv(db_session, bad_csv)
    assert summary.inserted_count == 1
    assert summary.invalid_count == 3
    assert len(summary.errors) == 3

def test_transaction_filtering(populated_db):
    # Filter by category
    params = TransactionFilterParams(category="Groceries")
    res = TransactionService.list_transactions(populated_db, params)
    assert res.total == 2
    assert all(t.category == "Groceries" for t in res.transactions)

    # Filter by transaction_type
    params_income = TransactionFilterParams(transaction_type="income")
    res_income = TransactionService.list_transactions(populated_db, params_income)
    assert res_income.total == 1
    assert res_income.transactions[0].amount == 5000.00

    # Filter by min_amount
    params_amount = TransactionFilterParams(min_amount=500.0)
    res_amount = TransactionService.list_transactions(populated_db, params_amount)
    assert res_amount.total == 3  # 5000.00, 1500.00, 600.00

def test_manual_transaction_create(db_session):
    trans_data = TransactionCreate(
        date="2026-08-18",
        amount=340.50,
        category="Shopping",
        description="Headphones",
        transaction_type="expense",
        payment_method="Credit Card",
        account="Primary Checking"
    )
    record, err = TransactionService.create_transaction(db_session, trans_data)
    assert err is None
    assert record is not None
    assert record.id is not None
    assert record.amount == 340.50

    # Attempting to insert identical record should trigger duplicate detection
    record_dup, err_dup = TransactionService.create_transaction(db_session, trans_data)
    assert record_dup is None
    assert "Duplicate" in err_dup
