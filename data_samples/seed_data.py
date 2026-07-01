"""Seed script to populate PostgreSQL with sample customers and transactions."""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime, timedelta
from decimal import Decimal
import random
import uuid

from sqlalchemy.orm import Session
from backend.database import engine, Base, SessionLocal
from backend.models import CustomerORM, TransactionORM


# Sample data for realistic generation
COUNTERPARTIES = [
    ("ABC Trading Co", "US"),
    ("XYZ Import LLC", "US"),
    ("Global Export Ltd", "UK"),
    ("Offshore Holdings", "Cayman Islands"),
    ("Pacific Ventures", "Hong Kong"),
    ("Euro Finance GmbH", "Germany"),
    ("Shell Company Inc", "Panama"),
    ("Sunrise Investments", "Singapore"),
    ("Mountain Trading", "Switzerland"),
    ("Desert Holdings", "UAE"),
    ("Nordic Partners", "Sweden"),
    ("Atlantic Commerce", "US"),
    ("Southern Goods LLC", "US"),
    ("Eastern Supplies", "China"),
    ("Western Logistics", "US"),
]

TRANSACTION_DESCRIPTIONS = [
    "Wire transfer",
    "ACH payment",
    "International wire",
    "Cash deposit",
    "Check deposit",
    "Wire out",
    "Payment received",
    "Invoice payment",
    "Trade settlement",
    "Loan repayment",
]


def create_customers():
    """Create 10 sample customers with varying risk profiles."""
    customers = [
        {
            "name": "Acme Trading LLC",
            "account_number": "ACC-001",
            "account_type": "Business",
            "country": "US",
            "occupation": "Import/Export Trading",
            "risk_rating": "High",
            "pep_status": False,
            "sanctions_match": False,
        },
        {
            "name": "Global Finance Corp",
            "account_number": "ACC-002",
            "account_type": "Business",
            "country": "UK",
            "occupation": "Financial Services",
            "risk_rating": "Medium",
            "pep_status": True,
            "sanctions_match": False,
        },
        {
            "name": "Local Retail Shop",
            "account_number": "ACC-003",
            "account_type": "Business",
            "country": "US",
            "occupation": "Retail Trade",
            "risk_rating": "Low",
            "pep_status": False,
            "sanctions_match": False,
        },
        {
            "name": "Offshore Investments Ltd",
            "account_number": "ACC-004",
            "account_type": "Business",
            "country": "Cayman Islands",
            "occupation": "Investment Management",
            "risk_rating": "High",
            "pep_status": False,
            "sanctions_match": True,
        },
        {
            "name": "Tech Startup Inc",
            "account_number": "ACC-005",
            "account_type": "Business",
            "country": "US",
            "occupation": "Software Development",
            "risk_rating": "Low",
            "pep_status": False,
            "sanctions_match": False,
        },
        {
            "name": "John Smith",
            "account_number": "ACC-006",
            "account_type": "Personal",
            "country": "US",
            "occupation": "Real Estate Agent",
            "risk_rating": "Medium",
            "pep_status": False,
            "sanctions_match": False,
        },
        {
            "name": "Pacific Trading Group",
            "account_number": "ACC-007",
            "account_type": "Business",
            "country": "Hong Kong",
            "occupation": "Wholesale Trade",
            "risk_rating": "High",
            "pep_status": False,
            "sanctions_match": False,
        },
        {
            "name": "Maria Garcia",
            "account_number": "ACC-008",
            "account_type": "Personal",
            "country": "US",
            "occupation": "Restaurant Owner",
            "risk_rating": "Low",
            "pep_status": False,
            "sanctions_match": False,
        },
        {
            "name": "Euro Import Export",
            "account_number": "ACC-009",
            "account_type": "Business",
            "country": "Germany",
            "occupation": "Import/Export",
            "risk_rating": "Medium",
            "pep_status": False,
            "sanctions_match": False,
        },
        {
            "name": "Suspicious Shell Co",
            "account_number": "ACC-010",
            "account_type": "Business",
            "country": "Panama",
            "occupation": "Consulting",
            "risk_rating": "High",
            "pep_status": True,
            "sanctions_match": True,
        },
    ]
    return customers


def generate_transactions_for_customer(customer_id: uuid.UUID, risk_rating: str, num_transactions: int = 15):
    """Generate transactions with patterns based on risk rating."""
    transactions = []
    base_date = datetime.now() - timedelta(days=90)

    for i in range(num_transactions):
        txn_date = base_date + timedelta(days=random.randint(0, 89), hours=random.randint(0, 23))
        counterparty, counterparty_country = random.choice(COUNTERPARTIES)

        if risk_rating == "High":
            # High-risk customers have suspicious patterns
            if i % 5 == 0:
                # Structuring: amounts just below $10,000
                amount = Decimal(str(random.uniform(9200, 9900)))
            elif i % 7 == 0:
                # Large round amounts
                amount = Decimal(str(random.choice([50000, 75000, 100000, 150000])))
            else:
                amount = Decimal(str(random.uniform(5000, 50000)))

            # More cross-border for high risk
            if random.random() > 0.3:
                counterparty, counterparty_country = random.choice([
                    ("Offshore Holdings", "Cayman Islands"),
                    ("Shell Company Inc", "Panama"),
                    ("Pacific Ventures", "Hong Kong"),
                    ("Desert Holdings", "UAE"),
                ])
        elif risk_rating == "Medium":
            # Medium risk - some suspicious activity
            if i % 8 == 0:
                amount = Decimal(str(random.uniform(9500, 9900)))
            else:
                amount = Decimal(str(random.uniform(1000, 25000)))
        else:
            # Low risk - normal activity
            amount = Decimal(str(random.uniform(100, 5000)))

        amount = round(amount, 2)
        txn_type = random.choice(["credit", "debit"])
        description = random.choice(TRANSACTION_DESCRIPTIONS)

        transactions.append({
            "customer_id": customer_id,
            "date": txn_date,
            "amount": amount,
            "currency": "USD",
            "transaction_type": txn_type,
            "counterparty": counterparty,
            "counterparty_country": counterparty_country,
            "description": description,
        })

    return transactions


def add_structuring_pattern(customer_id: uuid.UUID, transactions: list):
    """Add clear structuring pattern to a customer's transactions."""
    base_date = datetime.now() - timedelta(days=30)

    # Multiple transactions just below $10,000 on same day
    for i in range(5):
        transactions.append({
            "customer_id": customer_id,
            "date": base_date + timedelta(hours=i*2),
            "amount": Decimal(str(random.uniform(9400, 9700))),
            "currency": "USD",
            "transaction_type": "credit",
            "counterparty": "Various Cash Deposits",
            "counterparty_country": "US",
            "description": "Cash deposit",
        })

    return transactions


def add_rapid_movement_pattern(customer_id: uuid.UUID, transactions: list):
    """Add rapid movement pattern (quick in-out)."""
    base_date = datetime.now() - timedelta(days=15)

    # Large credit followed by immediate debit
    transactions.append({
        "customer_id": customer_id,
        "date": base_date,
        "amount": Decimal("75000.00"),
        "currency": "USD",
        "transaction_type": "credit",
        "counterparty": "Unknown Source Ltd",
        "counterparty_country": "Cayman Islands",
        "description": "Wire transfer received",
    })
    transactions.append({
        "customer_id": customer_id,
        "date": base_date + timedelta(hours=4),
        "amount": Decimal("74500.00"),
        "currency": "USD",
        "transaction_type": "debit",
        "counterparty": "Offshore Holdings",
        "counterparty_country": "Panama",
        "description": "Wire transfer out",
    })

    return transactions


def add_funnel_pattern(customer_id: uuid.UUID, transactions: list):
    """Add funnel pattern (multiple sources to single destination)."""
    base_date = datetime.now() - timedelta(days=20)

    # Multiple small credits from different sources
    sources = [
        ("Person A", "US"),
        ("Person B", "US"),
        ("Person C", "US"),
        ("Person D", "US"),
        ("Person E", "US"),
    ]

    total = Decimal("0")
    for i, (source, country) in enumerate(sources):
        amount = Decimal(str(random.uniform(3000, 6000)))
        total += amount
        transactions.append({
            "customer_id": customer_id,
            "date": base_date + timedelta(days=i),
            "amount": amount,
            "currency": "USD",
            "transaction_type": "credit",
            "counterparty": source,
            "counterparty_country": country,
            "description": "Payment received",
        })

    # Single large outgoing wire
    transactions.append({
        "customer_id": customer_id,
        "date": base_date + timedelta(days=6),
        "amount": total - Decimal("500"),
        "currency": "USD",
        "transaction_type": "debit",
        "counterparty": "Single Destination LLC",
        "counterparty_country": "Hong Kong",
        "description": "Wire transfer",
    })

    return transactions


def seed_database():
    """Main function to seed the database."""
    print("Creating database tables...")
    Base.metadata.create_all(bind=engine)

    db: Session = SessionLocal()

    try:
        # Check if data already exists
        existing_customers = db.query(CustomerORM).count()
        if existing_customers > 0:
            print(f"Database already has {existing_customers} customers. Skipping seed.")
            print("To reseed, drop the tables first.")
            return

        print("Creating customers...")
        customers_data = create_customers()
        customer_objects = []

        for cust_data in customers_data:
            customer = CustomerORM(
                id=uuid.uuid4(),
                **cust_data
            )
            db.add(customer)
            customer_objects.append(customer)

        db.flush()  # Get IDs assigned

        print("Creating transactions...")
        all_transactions = []

        for customer in customer_objects:
            # Determine number of transactions based on risk
            if customer.risk_rating == "High":
                num_txns = random.randint(15, 25)
            elif customer.risk_rating == "Medium":
                num_txns = random.randint(10, 15)
            else:
                num_txns = random.randint(5, 10)

            txns = generate_transactions_for_customer(customer.id, customer.risk_rating, num_txns)

            # Add specific patterns for high-risk customers
            if customer.name == "Acme Trading LLC":
                txns = add_structuring_pattern(customer.id, txns)
            elif customer.name == "Offshore Investments Ltd":
                txns = add_rapid_movement_pattern(customer.id, txns)
            elif customer.name == "Pacific Trading Group":
                txns = add_funnel_pattern(customer.id, txns)
            elif customer.name == "Suspicious Shell Co":
                txns = add_structuring_pattern(customer.id, txns)
                txns = add_rapid_movement_pattern(customer.id, txns)

            all_transactions.extend(txns)

        # Create transaction objects
        for txn_data in all_transactions:
            txn = TransactionORM(
                id=uuid.uuid4(),
                **txn_data
            )
            db.add(txn)

        db.commit()

        # Print summary
        total_customers = db.query(CustomerORM).count()
        total_transactions = db.query(TransactionORM).count()

        print(f"\nDatabase seeded successfully!")
        print(f"  Customers: {total_customers}")
        print(f"  Transactions: {total_transactions}")
        print("\nCustomers by risk rating:")

        for rating in ["High", "Medium", "Low"]:
            count = db.query(CustomerORM).filter(CustomerORM.risk_rating == rating).count()
            print(f"  {rating}: {count}")

        print("\nHigh-risk customers with embedded patterns:")
        print("  - Acme Trading LLC: Structuring pattern")
        print("  - Offshore Investments Ltd: Rapid movement pattern")
        print("  - Pacific Trading Group: Funnel pattern")
        print("  - Suspicious Shell Co: Structuring + Rapid movement")

    except Exception as e:
        db.rollback()
        print(f"Error seeding database: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed_database()
