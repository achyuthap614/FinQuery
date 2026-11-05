"""Tests for Financial Tool Registry, Security Boundaries, and Execution Engine."""
import pytest
from src.tools.financial_tools import execute_financial_tool, TOOL_REGISTRY

def test_registry_contains_required_tools():
    expected_tools = {
        "get_total_income",
        "get_total_expenses",
        "get_net_balance",
        "get_category_spending",
        "get_monthly_summary",
        "get_largest_transactions",
        "compare_monthly_spending",
        "get_unusual_spending"
    }
    assert expected_tools.issubset(set(TOOL_REGISTRY.keys()))

def test_tool_get_total_income(populated_db):
    res = execute_financial_tool("get_total_income", {}, populated_db)
    assert res["success"] is True
    assert res["result"]["value"] == 5000.00
    assert "evidence_source" in res["result"]

def test_tool_get_total_expenses(populated_db):
    res = execute_financial_tool("get_total_expenses", {}, populated_db)
    assert res["success"] is True
    assert res["result"]["value"] == pytest.approx(2495.50, 0.01)

def test_tool_get_net_balance(populated_db):
    res = execute_financial_tool("get_net_balance", {}, populated_db)
    assert res["success"] is True
    assert res["result"]["net_balance"] == pytest.approx(2504.50, 0.01)

def test_tool_get_category_spending(populated_db):
    res = execute_financial_tool("get_category_spending", {"category": "Groceries"}, populated_db)
    assert res["success"] is True
    assert res["result"]["total_spending"] == pytest.approx(270.50, 0.01)

def test_tool_get_largest_transactions(populated_db):
    res = execute_financial_tool("get_largest_transactions", {"limit": 2, "transaction_type": "expense"}, populated_db)
    assert res["success"] is True
    assert len(res["result"]["largest_transactions"]) == 2
    assert res["result"]["largest_transactions"][0]["amount"] == 1500.00

def test_tool_security_rejection_unregistered(populated_db):
    """Verifies that arbitrary or unknown tool calls are strictly rejected."""
    res = execute_financial_tool("execute_arbitrary_sql", {"sql": "DROP TABLE transactions"}, populated_db)
    assert res["success"] is False
    assert "Security Error" in res["error"]

def test_tool_validation_error_invalid_arguments(populated_db):
    """Verifies that invalid parameter types or ranges are rejected by Pydantic validation."""
    # Largest transactions limit cannot exceed 50
    res = execute_financial_tool("get_largest_transactions", {"limit": 9999}, populated_db)
    assert res["success"] is False
    assert "error" in res
