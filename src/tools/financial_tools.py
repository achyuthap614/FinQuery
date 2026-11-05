"""Financial Tool Registry and Execution Engine for LLM Tool Calling.

Security guarantees:
1. Whitelist-only: strictly registered tool functions.
2. No arbitrary SQL or Python code execution.
3. Strict Pydantic argument validation before invoking database routines.
4. Returns verifiable numerical evidence directly from the database.
"""
from typing import Dict, Any, Optional, List, Callable
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.orm import Session
from src.services.analytics_service import AnalyticsService
from src.utils.logger import logger
import re

# ==========================================
# Tool Input Schemas (Strict Pydantic Validation)
# ==========================================

class TotalIncomeArgs(BaseModel):
    start_date: Optional[str] = Field(None, description="Start date in YYYY-MM-DD format")
    end_date: Optional[str] = Field(None, description="End date in YYYY-MM-DD format")

    @field_validator("start_date", "end_date")
    @classmethod
    def check_date(cls, v):
        if v and not re.match(r"^\d{4}-\d{2}(-\d{2})?$", v.strip()):
            raise ValueError("Date must be in YYYY-MM or YYYY-MM-DD format")
        return v.strip() if v else None

class TotalExpensesArgs(BaseModel):
    start_date: Optional[str] = Field(None, description="Start date in YYYY-MM-DD format")
    end_date: Optional[str] = Field(None, description="End date in YYYY-MM-DD format")

class NetBalanceArgs(BaseModel):
    start_date: Optional[str] = Field(None, description="Start date in YYYY-MM-DD format")
    end_date: Optional[str] = Field(None, description="End date in YYYY-MM-DD format")

class CategorySpendingArgs(BaseModel):
    category: Optional[str] = Field(None, description="Specific category name, e.g. 'Food', 'Groceries', 'Rent', 'Travel'")
    start_date: Optional[str] = Field(None, description="Start date in YYYY-MM-DD format")
    end_date: Optional[str] = Field(None, description="End date in YYYY-MM-DD format")

class MonthlySummaryArgs(BaseModel):
    month: Optional[str] = Field(None, description="Specific month in YYYY-MM format, e.g. '2026-08'")

    @field_validator("month")
    @classmethod
    def check_month(cls, v):
        if v and not re.match(r"^\d{4}-\d{2}$", v.strip()):
            raise ValueError("Month must be in YYYY-MM format")
        return v.strip() if v else None

class LargestTransactionsArgs(BaseModel):
    limit: int = Field(5, ge=1, le=50, description="Number of largest transactions to return (1-50)")
    transaction_type: str = Field("expense", description="'expense' or 'income'")

class CompareMonthlySpendingArgs(BaseModel):
    month1: str = Field(..., description="First month in YYYY-MM format, e.g. '2026-07'")
    month2: str = Field(..., description="Second month in YYYY-MM format, e.g. '2026-08'")

    @field_validator("month1", "month2")
    @classmethod
    def check_month_format(cls, v):
        if not re.match(r"^\d{4}-\d{2}$", v.strip()):
            raise ValueError("Month format must be YYYY-MM")
        return v.strip()

class UnusualSpendingArgs(BaseModel):
    threshold_std: float = Field(2.0, ge=1.0, le=5.0, description="Z-Score standard deviation threshold (default 2.0)")


# ==========================================
# Tool Implementations
# ==========================================

def tool_get_total_income(db: Session, args: TotalIncomeArgs) -> Dict[str, Any]:
    summary = AnalyticsService.get_financial_summary(db, start_date=args.start_date, end_date=args.end_date)
    return {
        "metric": "total_income",
        "value": summary.total_income,
        "currency": "USD",
        "start_date": args.start_date,
        "end_date": args.end_date,
        "transactions_analyzed": summary.total_transactions,
        "evidence_source": "SQLite transactions table (SUM(amount) WHERE transaction_type='income')"
    }

def tool_get_total_expenses(db: Session, args: TotalExpensesArgs) -> Dict[str, Any]:
    summary = AnalyticsService.get_financial_summary(db, start_date=args.start_date, end_date=args.end_date)
    return {
        "metric": "total_expenses",
        "value": summary.total_expenses,
        "currency": "USD",
        "start_date": args.start_date,
        "end_date": args.end_date,
        "transactions_analyzed": summary.total_transactions,
        "evidence_source": "SQLite transactions table (SUM(amount) WHERE transaction_type='expense')"
    }

def tool_get_net_balance(db: Session, args: NetBalanceArgs) -> Dict[str, Any]:
    summary = AnalyticsService.get_financial_summary(db, start_date=args.start_date, end_date=args.end_date)
    return {
        "metric": "net_balance",
        "total_income": summary.total_income,
        "total_expenses": summary.total_expenses,
        "net_balance": summary.net_balance,
        "savings_rate_percent": summary.savings_rate_percent,
        "currency": "USD",
        "evidence_source": "SQLite calculation: Total Income - Total Expenses"
    }

def tool_get_category_spending(db: Session, args: CategorySpendingArgs) -> Dict[str, Any]:
    breakdown = AnalyticsService.get_category_spending(
        db,
        category=args.category,
        start_date=args.start_date,
        end_date=args.end_date,
        transaction_type="expense"
    )
    items = [b.model_dump() for b in breakdown]
    total_spending = sum(b.total_amount for b in breakdown)
    return {
        "category_queried": args.category or "all",
        "total_spending": round(total_spending, 2),
        "breakdown": items,
        "evidence_source": "SQLite transactions table grouped by category"
    }

def tool_get_monthly_summary(db: Session, args: MonthlySummaryArgs) -> Dict[str, Any]:
    monthly_data = AnalyticsService.get_monthly_spending(db)
    if args.month:
        matched = [m for m in monthly_data if m.month == args.month]
        if not matched:
            return {
                "month": args.month,
                "found": False,
                "message": f"No transactions recorded for month {args.month}",
                "available_months": [m.month for m in monthly_data]
            }
        item = matched[0]
        return {
            "month": item.month,
            "income": item.income,
            "expenses": item.expenses,
            "net_balance": item.net,
            "transaction_count": item.transaction_count,
            "evidence_source": f"SQLite aggregations for month {args.month}"
        }
    return {
        "all_months": [m.model_dump() for m in monthly_data],
        "evidence_source": "SQLite monthly aggregation"
    }

def tool_get_largest_transactions(db: Session, args: LargestTransactionsArgs) -> Dict[str, Any]:
    records = AnalyticsService.get_largest_transactions(
        db,
        limit=args.limit,
        transaction_type=args.transaction_type
    )
    return {
        "count": len(records),
        "transaction_type": args.transaction_type,
        "largest_transactions": records,
        "evidence_source": f"SQLite transactions table ORDER BY amount DESC LIMIT {args.limit}"
    }

def tool_compare_monthly_spending(db: Session, args: CompareMonthlySpendingArgs) -> Dict[str, Any]:
    result = AnalyticsService.compare_monthly_spending(db, args.month1, args.month2)
    return {
        "month1": result.month1,
        "month2": result.month2,
        "month1_expenses": result.month1_expenses,
        "month2_expenses": result.month2_expenses,
        "expense_difference": result.expense_difference,
        "expense_percentage_change": result.expense_percentage_change,
        "month1_income": result.month1_income,
        "month2_income": result.month2_income,
        "category_breakdown": [c.model_dump() for c in result.category_breakdown],
        "evidence_source": f"Comparative SQLite aggregation between {args.month1} and {args.month2}"
    }

def tool_get_unusual_spending(db: Session, args: UnusualSpendingArgs) -> Dict[str, Any]:
    anomalies = AnalyticsService.get_unusual_spending(db, threshold_z=args.threshold_std)
    return {
        "detection_method": anomalies.method,
        "threshold_z": anomalies.threshold_z,
        "anomalies_detected": anomalies.total_anomalies_found,
        "unusual_transactions": [a.model_dump() for a in anomalies.anomalies],
        "evidence_source": f"Statistical sample standard deviation calculation with Z-score threshold {args.threshold_std}"
    }


# ==========================================
# Tool Registry Mapping & Dispatcher
# ==========================================

TOOL_REGISTRY: Dict[str, Dict[str, Any]] = {
    "get_total_income": {
        "func": tool_get_total_income,
        "schema": TotalIncomeArgs,
        "description": "Calculates total financial income across all records or an optional date range (YYYY-MM-DD).",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "start_date": {"type": "STRING", "description": "Optional start date YYYY-MM-DD"},
                "end_date": {"type": "STRING", "description": "Optional end date YYYY-MM-DD"}
            }
        }
    },
    "get_total_expenses": {
        "func": tool_get_total_expenses,
        "schema": TotalExpensesArgs,
        "description": "Calculates total expenses across all records or an optional date range (YYYY-MM-DD).",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "start_date": {"type": "STRING", "description": "Optional start date YYYY-MM-DD"},
                "end_date": {"type": "STRING", "description": "Optional end date YYYY-MM-DD"}
            }
        }
    },
    "get_net_balance": {
        "func": tool_get_net_balance,
        "schema": NetBalanceArgs,
        "description": "Calculates net balance (Total Income - Total Expenses) and savings rate.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "start_date": {"type": "STRING", "description": "Optional start date YYYY-MM-DD"},
                "end_date": {"type": "STRING", "description": "Optional end date YYYY-MM-DD"}
            }
        }
    },
    "get_category_spending": {
        "func": tool_get_category_spending,
        "schema": CategorySpendingArgs,
        "description": "Calculates spending breakdown by category, or queries spending for a specific category (e.g. food, rent, shopping).",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "category": {"type": "STRING", "description": "Category name to filter, e.g. 'Groceries', 'Dining', 'Rent'"},
                "start_date": {"type": "STRING", "description": "Optional start date YYYY-MM-DD"},
                "end_date": {"type": "STRING", "description": "Optional end date YYYY-MM-DD"}
            }
        }
    },
    "get_monthly_summary": {
        "func": tool_get_monthly_summary,
        "schema": MonthlySummaryArgs,
        "description": "Retrieves income, expenses, and net balance for a specific month (YYYY-MM) or all recorded months.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "month": {"type": "STRING", "description": "Month in YYYY-MM format, e.g. '2026-08'"}
            }
        }
    },
    "get_largest_transactions": {
        "func": tool_get_largest_transactions,
        "schema": LargestTransactionsArgs,
        "description": "Retrieves the highest value expense or income transactions.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "limit": {"type": "INTEGER", "description": "Number of top transactions (default 5)"},
                "transaction_type": {"type": "STRING", "description": "'expense' or 'income'"}
            }
        }
    },
    "compare_monthly_spending": {
        "func": tool_compare_monthly_spending,
        "schema": CompareMonthlySpendingArgs,
        "description": "Compares spending differences, category shifts, and percentage changes between two months.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "month1": {"type": "STRING", "description": "First month YYYY-MM, e.g. '2026-07'"},
                "month2": {"type": "STRING", "description": "Second month YYYY-MM, e.g. '2026-08'"}
            },
            "required": ["month1", "month2"]
        }
    },
    "get_unusual_spending": {
        "func": tool_get_unusual_spending,
        "schema": UnusualSpendingArgs,
        "description": "Detects statistically unusual spending anomalies where transaction amounts exceed category standard deviations.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "threshold_std": {"type": "NUMBER", "description": "Z-Score deviation threshold (default 2.0)"}
            }
        }
    }
}

def execute_financial_tool(tool_name: str, raw_arguments: Dict[str, Any], db: Session) -> Dict[str, Any]:
    """
    Safely executes a registered tool function.
    Validates arguments via Pydantic model and handles errors securely.
    """
    if tool_name not in TOOL_REGISTRY:
        error_msg = f"Security Error: Tool '{tool_name}' is not in the approved financial tools registry."
        logger.warning(error_msg)
        return {"success": False, "error": error_msg, "tool_name": tool_name}

    tool_def = TOOL_REGISTRY[tool_name]
    schema_cls = tool_def["schema"]
    func_callable: Callable = tool_def["func"]

    try:
        # Validate arguments using schema model
        validated_args = schema_cls(**(raw_arguments or {}))
        result = func_callable(db, validated_args)
        return {
            "success": True,
            "tool_name": tool_name,
            "arguments": raw_arguments,
            "result": result
        }
    except Exception as exc:
        logger.error(f"Error executing tool {tool_name} with args {raw_arguments}: {exc}")
        return {
            "success": False,
            "tool_name": tool_name,
            "arguments": raw_arguments,
            "error": str(exc)
        }
