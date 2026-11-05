"""Transaction business logic and data persistence service."""
import csv
import io
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import func, or_
from src.database.models import Transaction
from src.schemas.transaction import (
    TransactionCreate,
    TransactionFilterParams,
    TransactionUploadSummary,
    TransactionListResponse,
    TransactionRead
)
from src.utils.logger import logger

class TransactionService:
    @staticmethod
    def normalize_date(date_str: str) -> str:
        """Parses common date formats and returns ISO YYYY-MM-DD string."""
        date_str = str(date_str).strip()
        common_formats = [
            "%Y-%m-%d",
            "%d-%m-%Y",
            "%m/%d/%Y",
            "%d/%m/%Y",
            "%Y/%m/%d",
            "%Y.%m.%d",
            "%d.%m.%Y"
        ]
        for fmt in common_formats:
            try:
                dt = datetime.strptime(date_str, fmt)
                return dt.strftime("%Y-%m-%d")
            except ValueError:
                continue
        raise ValueError(f"Invalid date format '{date_str}'. Expected YYYY-MM-DD or standard date format.")

    @staticmethod
    def parse_amount(amount_val: Any) -> float:
        """Sanitizes amount string into a positive float."""
        if isinstance(amount_val, (int, float)):
            val = float(amount_val)
        else:
            s = str(amount_val).strip().replace("$", "").replace("₹", "").replace("€", "").replace(",", "")
            val = float(s)
        if val <= 0:
            raise ValueError(f"Amount must be strictly greater than 0, got {val}")
        return round(val, 2)

    @classmethod
    def create_transaction(cls, db: Session, trans_data: TransactionCreate) -> Tuple[Optional[Transaction], Optional[str]]:
        """Creates a single transaction with duplicate detection."""
        normalized_date = cls.normalize_date(trans_data.date)
        amount = cls.parse_amount(trans_data.amount)
        category = trans_data.category.strip()
        description = trans_data.description.strip()
        t_type = trans_data.transaction_type.strip().lower()

        if t_type not in ("income", "expense"):
            return None, "Transaction type must be 'income' or 'expense'"

        fp = Transaction.generate_fingerprint(normalized_date, amount, category, description, t_type)

        existing = db.query(Transaction).filter(Transaction.fingerprint == fp).first()
        if existing:
            return None, "Duplicate transaction detected"

        new_trans = Transaction(
            date=normalized_date,
            amount=amount,
            category=category,
            description=description,
            transaction_type=t_type,
            payment_method=trans_data.payment_method or "Bank Transfer",
            account=trans_data.account or "Primary Account",
            fingerprint=fp
        )
        db.add(new_trans)
        db.commit()
        db.refresh(new_trans)
        return new_trans, None

    @classmethod
    def import_csv(cls, db: Session, csv_content: str) -> TransactionUploadSummary:
        """Parses CSV content, validates each row, checks duplicates, and inserts valid rows."""
        summary = TransactionUploadSummary(
            total_processed=0,
            inserted_count=0,
            duplicate_count=0,
            invalid_count=0,
            errors=[]
        )

        try:
            reader = csv.DictReader(io.StringIO(csv_content))
            if not reader.fieldnames:
                summary.errors.append({"row": 0, "error": "CSV file is empty or headers are missing."})
                return summary

            # Normalize header names (lowercase, strip whitespace, remove underscores/spaces)
            header_map = {}
            for col in reader.fieldnames:
                clean_col = col.strip().lower().replace("_", "").replace(" ", "")
                header_map[clean_col] = col

            def get_col_val(row_dict: dict, *candidates):
                for cand in candidates:
                    clean_cand = cand.lower().replace("_", "").replace(" ", "")
                    if clean_cand in header_map:
                        val = row_dict.get(header_map[clean_cand])
                        if val is not None and str(val).strip() != "":
                            return str(val).strip()
                return None

            seen_batch_fingerprints = set()
            transactions_to_insert = []

            for row_idx, row in enumerate(reader, start=2):  # line 2 is first data row
                summary.total_processed += 1
                try:
                    date_val = get_col_val(row, "date", "trans_date", "transaction_date")
                    amount_val = get_col_val(row, "amount", "value", "cost")
                    category_val = get_col_val(row, "category", "cat", "tag")
                    desc_val = get_col_val(row, "description", "desc", "merchant", "payee", "note")
                    type_val = get_col_val(row, "type", "transaction_type", "trans_type", "kind")
                    payment_method = get_col_val(row, "payment_method", "paymentmethod", "payment", "mode") or "Bank Transfer"
                    account = get_col_val(row, "account", "account_name", "wallet") or "Primary Account"

                    if not date_val:
                        raise ValueError("Missing 'date' field.")
                    if not amount_val:
                        raise ValueError("Missing 'amount' field.")
                    if not category_val:
                        raise ValueError("Missing 'category' field.")
                    if not desc_val:
                        raise ValueError("Missing 'description' field.")

                    normalized_date = cls.normalize_date(date_val)
                    amount = cls.parse_amount(amount_val)

                    # Infer or validate transaction type
                    if type_val:
                        clean_type = type_val.lower().strip()
                        if clean_type in ("income", "deposit", "credit", "salary"):
                            trans_type = "income"
                        elif clean_type in ("expense", "debit", "withdrawal", "payment", "purchase"):
                            trans_type = "expense"
                        else:
                            raise ValueError(f"Unrecognized transaction type '{type_val}'.")
                    else:
                        # Auto-infer based on common categories
                        income_categories = {"salary", "freelance", "investment return", "dividend", "bonus", "refund", "interest"}
                        if category_val.lower() in income_categories:
                            trans_type = "income"
                        else:
                            trans_type = "expense"

                    fingerprint = Transaction.generate_fingerprint(
                        normalized_date, amount, category_val, desc_val, trans_type
                    )

                    if fingerprint in seen_batch_fingerprints:
                        summary.duplicate_count += 1
                        continue

                    # Check database for existing duplicate
                    existing = db.query(Transaction).filter(Transaction.fingerprint == fingerprint).first()
                    if existing:
                        summary.duplicate_count += 1
                        seen_batch_fingerprints.add(fingerprint)
                        continue

                    seen_batch_fingerprints.add(fingerprint)
                    trans_obj = Transaction(
                        date=normalized_date,
                        amount=amount,
                        category=category_val,
                        description=desc_val,
                        transaction_type=trans_type,
                        payment_method=payment_method,
                        account=account,
                        fingerprint=fingerprint
                    )
                    transactions_to_insert.append(trans_obj)

                except Exception as err:
                    summary.invalid_count += 1
                    summary.errors.append({
                        "row": row_idx,
                        "data": dict(row),
                        "error": str(err)
                    })

            if transactions_to_insert:
                db.bulk_save_objects(transactions_to_insert)
                db.commit()
                summary.inserted_count = len(transactions_to_insert)
                logger.info(f"Imported {summary.inserted_count} new transactions. Duplicates: {summary.duplicate_count}. Errors: {summary.invalid_count}.")

        except Exception as file_err:
            logger.error(f"Failed to process CSV import: {file_err}")
            summary.errors.append({"row": 0, "error": f"CSV parse failure: {str(file_err)}"})

        return summary

    @classmethod
    def list_transactions(cls, db: Session, params: TransactionFilterParams) -> TransactionListResponse:
        """Filters, sorts, and paginates transaction records."""
        query = db.query(Transaction)

        if params.start_date:
            query = query.filter(Transaction.date >= params.start_date)
        if params.end_date:
            query = query.filter(Transaction.date <= params.end_date)
        if params.category:
            query = query.filter(Transaction.category.ilike(f"%{params.category}%"))
        if params.transaction_type:
            query = query.filter(Transaction.transaction_type == params.transaction_type.lower())
        if params.min_amount is not None:
            query = query.filter(Transaction.amount >= params.min_amount)
        if params.max_amount is not None:
            query = query.filter(Transaction.amount <= params.max_amount)
        if params.search_query:
            search = f"%{params.search_query}%"
            query = query.filter(or_(
                Transaction.description.ilike(search),
                Transaction.category.ilike(search),
                Transaction.account.ilike(search)
            ))

        total = query.count()
        records = query.order_by(Transaction.date.desc(), Transaction.id.desc()).offset(params.offset).limit(params.limit).all()

        return TransactionListResponse(
            total=total,
            limit=params.limit,
            offset=params.offset,
            transactions=[TransactionRead.model_validate(t) for t in records]
        )

    @classmethod
    def get_by_id(cls, db: Session, transaction_id: int) -> Optional[Transaction]:
        return db.query(Transaction).filter(Transaction.id == transaction_id).first()

    @classmethod
    def clear_all(cls, db: Session) -> int:
        """Deletes all transactions (used for resetting demo state)."""
        deleted = db.query(Transaction).delete()
        db.commit()
        logger.info(f"Cleared {deleted} transactions from database.")
        return deleted
