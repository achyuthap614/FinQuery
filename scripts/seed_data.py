"""Synthetic data generator and database seeder for FinQuery."""
import csv
import random
from datetime import datetime, timedelta
from pathlib import Path
from src.database.database import init_db, SessionLocal
from src.services.transaction_service import TransactionService
from src.utils.config import settings
from src.utils.logger import logger

def generate_synthetic_transactions(output_csv: Path) -> int:
    """Generates 130+ realistic, internally consistent synthetic financial transactions."""
    random.seed(42)  # Deterministic seed for reproducible testing

    transactions = []

    # 6 Months date range: May 1, 2026 to October 31, 2026
    start_date = datetime(2026, 5, 1)

    # 1. Fixed Recurring Monthly Income & Expenses
    for month_offset in range(6):
        month_dt = start_date + timedelta(days=month_offset * 30 + 1)
        year_str = month_dt.strftime("%Y")
        month_str = month_dt.strftime("%m")

        # Salary on 1st
        transactions.append({
            "date": f"{year_str}-{month_str}-01",
            "amount": 5500.00,
            "category": "Salary",
            "description": "Tech Corp Monthly Payroll Direct Deposit",
            "transaction_type": "income",
            "payment_method": "Direct Deposit",
            "account": "Primary Checking"
        })

        # Rent on 2nd
        transactions.append({
            "date": f"{year_str}-{month_str}-02",
            "amount": 1650.00,
            "category": "Rent",
            "description": "Metropolitan Apartments Monthly Rent",
            "transaction_type": "expense",
            "payment_method": "ACH Transfer",
            "account": "Primary Checking"
        })

        # Utilities on 5th
        transactions.append({
            "date": f"{year_str}-{month_str}-05",
            "amount": round(random.uniform(95.0, 145.0), 2),
            "category": "Utilities",
            "description": "City Power & Gas Electric Bill",
            "transaction_type": "expense",
            "payment_method": "Autopay",
            "account": "Primary Checking"
        })

        # Internet on 8th
        transactions.append({
            "date": f"{year_str}-{month_str}-08",
            "amount": 75.00,
            "category": "Utilities",
            "description": "Fiber Optic High-Speed Internet",
            "transaction_type": "expense",
            "payment_method": "Credit Card",
            "account": "Rewards Credit Card"
        })

        # Subscriptions on 10th - 15th
        transactions.append({
            "date": f"{year_str}-{month_str}-10",
            "amount": 19.99,
            "category": "Subscriptions",
            "description": "Netflix Premium 4K",
            "transaction_type": "expense",
            "payment_method": "Credit Card",
            "account": "Rewards Credit Card"
        })
        transactions.append({
            "date": f"{year_str}-{month_str}-12",
            "amount": 11.99,
            "category": "Subscriptions",
            "description": "Spotify Family Plan",
            "transaction_type": "expense",
            "payment_method": "Credit Card",
            "account": "Rewards Credit Card"
        })
        transactions.append({
            "date": f"{year_str}-{month_str}-15",
            "amount": 49.00,
            "category": "Subscriptions",
            "description": "Fitness & Climbing Gym Membership",
            "transaction_type": "expense",
            "payment_method": "Debit Card",
            "account": "Primary Checking"
        })

        # Freelance Income (every alternate month)
        if month_offset % 2 == 1:
            transactions.append({
                "date": f"{year_str}-{month_str}-18",
                "amount": round(random.choice([850.0, 1200.0, 1450.0]), 2),
                "category": "Freelance",
                "description": "UI/UX & Python Consulting Client Payout",
                "transaction_type": "income",
                "payment_method": "Bank Transfer",
                "account": "Primary Checking"
            })

        # Investment Dividend
        transactions.append({
            "date": f"{year_str}-{month_str}-25",
            "amount": round(random.uniform(120.0, 240.0), 2),
            "category": "Investment",
            "description": "Vanguard Total Stock Index Dividend",
            "transaction_type": "income",
            "payment_method": "Reinvestment/Deposit",
            "account": "Brokerage Account"
        })

    # 2. Variable Lifestyle Expenses (Groceries, Dining, Shopping, Travel, Gas, Pharmacy)
    merchants = {
        "Groceries": [
            ("Whole Foods Organic Market", (75.0, 185.0)),
            ("Trader Joe's Weekly Groceries", (45.0, 110.0)),
            ("Costco Wholesale Bulk Supply", (140.0, 290.0)),
            ("Local Farmers Market", (25.0, 65.0))
        ],
        "Dining": [
            ("Blue Bottle Artisan Coffee", (6.50, 14.0)),
            ("Chipotle Mexican Grill", (16.0, 24.0)),
            ("Osteria Italian Restaurant Dinner", (55.0, 115.0)),
            ("Tokyo Ramen House", (22.0, 42.0)),
            ("Sweetgreen Harvest Bowl", (15.0, 21.0))
        ],
        "Transportation": [
            ("Shell Gas Station Fuel", (42.0, 68.0)),
            ("Chevron Unleaded Gas", (40.0, 65.0)),
            ("Uber City Ride Downtown", (18.0, 36.0)),
            ("Metropolitan Transit Subway Pass", (32.0, 32.0))
        ],
        "Shopping": [
            ("Amazon Marketplace Essentials", (25.0, 85.0)),
            ("Target Home Goods & Apparel", (35.0, 95.0)),
            ("Nike Running Shoes", (110.0, 140.0)),
            ("Bookstore Literature & Tech Books", (28.0, 55.0))
        ],
        "Healthcare": [
            ("CVS Health Pharmacy Prescriptions", (18.0, 45.0)),
            ("Dental Hygiene & Prophylaxis", (120.0, 180.0)),
            ("Optometry Contact Lenses", (85.0, 150.0))
        ],
        "Entertainment": [
            ("AMC IMAX Movie Tickets & Popcorn", (26.0, 44.0)),
            ("Steam Indie Video Game Purchase", (19.99, 59.99)),
            ("Symphony Hall Concert Tickets", (65.0, 95.0))
        ]
    }

    current_day = start_date
    end_date = datetime(2026, 10, 31)

    while current_day <= end_date:
        # Every 3-4 days generate a grocery transaction
        if current_day.weekday() in (2, 6):
            store, (p_min, p_max) = random.choice(merchants["Groceries"])
            transactions.append({
                "date": current_day.strftime("%Y-%m-%d"),
                "amount": round(random.uniform(p_min, p_max), 2),
                "category": "Groceries",
                "description": store,
                "transaction_type": "expense",
                "payment_method": "Credit Card",
                "account": "Rewards Credit Card"
            })

        # Dining 2-3 times a week
        if current_day.weekday() in (1, 4, 5):
            restaurant, (p_min, p_max) = random.choice(merchants["Dining"])
            transactions.append({
                "date": current_day.strftime("%Y-%m-%d"),
                "amount": round(random.uniform(p_min, p_max), 2),
                "category": "Dining",
                "description": restaurant,
                "transaction_type": "expense",
                "payment_method": "Credit Card",
                "account": "Rewards Credit Card"
            })

        # Occasional shopping / transport
        if current_day.day in (7, 14, 21, 28):
            shop, (p_min, p_max) = random.choice(merchants["Shopping"])
            transactions.append({
                "date": current_day.strftime("%Y-%m-%d"),
                "amount": round(random.uniform(p_min, p_max), 2),
                "category": "Shopping",
                "description": shop,
                "transaction_type": "expense",
                "payment_method": "Credit Card",
                "account": "Rewards Credit Card"
            })

        if current_day.day in (4, 19):
            fuel, (p_min, p_max) = random.choice(merchants["Transportation"])
            transactions.append({
                "date": current_day.strftime("%Y-%m-%d"),
                "amount": round(random.uniform(p_min, p_max), 2),
                "category": "Transportation",
                "description": fuel,
                "transaction_type": "expense",
                "payment_method": "Debit Card",
                "account": "Primary Checking"
            })

        current_day += timedelta(days=1)

    # 3. Deliberate Statistical Anomalies (for unusual spending testing)
    transactions.append({
        "date": "2026-07-14",
        "amount": 745.00,
        "category": "Dining",
        "description": "Executive Anniversary Banquet Celebration",
        "transaction_type": "expense",
        "payment_method": "Credit Card",
        "account": "Rewards Credit Card"
    })
    transactions.append({
        "date": "2026-08-22",
        "amount": 2350.00,
        "category": "Shopping",
        "description": "Apple Store MacBook Pro Workstation Upgrade",
        "transaction_type": "expense",
        "payment_method": "Credit Card",
        "account": "Rewards Credit Card"
    })
    transactions.append({
        "date": "2026-09-12",
        "amount": 1420.00,
        "category": "Travel",
        "description": "International Roundtrip Airline Flight",
        "transaction_type": "expense",
        "payment_method": "Credit Card",
        "account": "Rewards Credit Card"
    })

    # Sort chronologically
    transactions.sort(key=lambda x: x["date"])

    output_csv.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = ["date", "amount", "category", "description", "transaction_type", "payment_method", "account"]

    with open(output_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(transactions)

    logger.info(f"Generated {len(transactions)} synthetic transactions at {output_csv}")
    return len(transactions)

def seed_database():
    """Initializes the database and imports generated CSV transactions."""
    init_db()
    csv_path = settings.TRANSACTIONS_CSV_PATH
    generate_synthetic_transactions(csv_path)

    with open(csv_path, "r", encoding="utf-8") as f:
        content = f.read()

    db = SessionLocal()
    try:
        # Clear existing records first
        TransactionService.clear_all(db)
        summary = TransactionService.import_csv(db, content)
        logger.info(f"Database seeded successfully: {summary.inserted_count} transactions inserted.")
        return summary
    finally:
        db.close()

if __name__ == "__main__":
    seed_database()
