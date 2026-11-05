"""SQLAlchemy database models for FinQuery."""
from datetime import datetime, timezone
import hashlib
from sqlalchemy import Column, Integer, Float, String, DateTime, Index
from src.database.database import Base

class Transaction(Base):
    """Transaction model representing financial income or expense."""
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    date = Column(String(10), nullable=False, index=True)  # YYYY-MM-DD
    amount = Column(Float, nullable=False)
    category = Column(String(50), nullable=False, index=True)
    description = Column(String(255), nullable=False)
    transaction_type = Column(String(10), nullable=False, index=True)  # 'income' or 'expense'
    payment_method = Column(String(50), nullable=True, default="Bank Transfer")
    account = Column(String(50), nullable=True, default="Primary Account")
    fingerprint = Column(String(64), nullable=False, unique=True, index=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        Index("ix_trans_date_type", "date", "transaction_type"),
        Index("ix_trans_cat_type", "category", "transaction_type"),
    )

    @staticmethod
    def generate_fingerprint(date_str: str, amount: float, category: str, description: str, transaction_type: str) -> str:
        """Computes a unique SHA-256 fingerprint for duplicate detection."""
        normalized = f"{date_str.strip()}|{float(amount):.2f}|{category.strip().lower()}|{description.strip().lower()}|{transaction_type.strip().lower()}"
        return hashlib.sha256(normalized.encode("utf-8")).hexdigest()

    def to_dict(self):
        """Converts model instance to dictionary representation."""
        return {
            "id": self.id,
            "date": self.date,
            "amount": self.amount,
            "category": self.category,
            "description": self.description,
            "transaction_type": self.transaction_type,
            "payment_method": self.payment_method,
            "account": self.account,
            "fingerprint": self.fingerprint,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }
