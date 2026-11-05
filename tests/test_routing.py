"""Tests for Intelligent Question Routing."""
import pytest
from src.llm.orchestrator import FinancialOrchestrator

@pytest.fixture
def orchestrator():
    return FinancialOrchestrator()

def test_route_sql_spending(orchestrator):
    decision = orchestrator.route_query("How much did I spend on groceries this month?")
    assert decision.route == "sql_tool"
    assert decision.confidence >= 0.85

def test_route_sql_income(orchestrator):
    decision = orchestrator.route_query("What is my total income and earnings?")
    assert decision.route == "sql_tool"

def test_route_sql_unusual(orchestrator):
    decision = orchestrator.route_query("Is my spending unusually high compared with previous months?")
    assert decision.route == "sql_tool"

def test_route_rag_compound_interest(orchestrator):
    decision = orchestrator.route_query("What is compound interest and the rule of 72?")
    assert decision.route == "rag_knowledge"
    assert decision.confidence >= 0.85

def test_route_rag_etf_vs_mutual_funds(orchestrator):
    decision = orchestrator.route_query("Explain the difference between mutual funds and ETFs.")
    assert decision.route == "rag_knowledge"

def test_route_hybrid_question(orchestrator):
    decision = orchestrator.route_query("How much did I spend on dining, and explain the 50/30/20 budgeting method?")
    assert decision.route == "hybrid"

def test_route_direct_greeting(orchestrator):
    decision = orchestrator.route_query("Hello there! Who are you?")
    assert decision.route == "direct_conversation"
