"""Schema validation for uploaded data."""

from typing import List, Dict, Any, Tuple
from datetime import datetime
import pandas as pd

from backend.models import TransactionRecord, KYCData


class ValidationError(Exception):
    """Custom validation error."""
    def __init__(self, errors: List[str]):
        self.errors = errors
        super().__init__(f"Validation failed: {', '.join(errors)}")


def validate_transaction_dataframe(df: pd.DataFrame) -> Tuple[List[Dict[str, Any]], List[str]]:
    """
    Validate and normalize transaction DataFrame.

    Returns tuple of (valid_records, error_messages).
    """
    errors = []
    records = []

    # Required columns (case-insensitive matching)
    required_cols = ["transaction_id", "date", "amount", "transaction_type", "counterparty"]
    optional_cols = ["currency", "counterparty_account", "country", "description"]

    # Normalize column names to lowercase
    df.columns = df.columns.str.lower().str.strip().str.replace(" ", "_")

    # Check required columns
    missing_cols = [col for col in required_cols if col not in df.columns]
    if missing_cols:
        errors.append(f"Missing required columns: {missing_cols}")
        return records, errors

    # Process each row
    for idx, row in df.iterrows():
        row_errors = []

        # Validate transaction_id
        txn_id = str(row.get("transaction_id", "")).strip()
        if not txn_id:
            row_errors.append(f"Row {idx}: Missing transaction_id")
            continue

        # Validate and parse date
        try:
            date_val = row.get("date")
            if pd.isna(date_val):
                row_errors.append(f"Row {idx}: Missing date")
                continue
            if isinstance(date_val, str):
                date_parsed = pd.to_datetime(date_val)
            else:
                date_parsed = pd.to_datetime(date_val)
        except Exception:
            row_errors.append(f"Row {idx}: Invalid date format")
            continue

        # Validate amount
        try:
            amount = float(row.get("amount", 0))
            if pd.isna(amount):
                row_errors.append(f"Row {idx}: Missing amount")
                continue
        except (ValueError, TypeError):
            row_errors.append(f"Row {idx}: Invalid amount")
            continue

        # Validate transaction_type
        txn_type = str(row.get("transaction_type", "")).strip().lower()
        if txn_type not in ["credit", "debit", "deposit", "withdrawal", "transfer_in", "transfer_out"]:
            row_errors.append(f"Row {idx}: Invalid transaction_type '{txn_type}'")
            continue

        # Normalize transaction type
        if txn_type in ["credit", "deposit", "transfer_in"]:
            txn_type = "credit"
        else:
            txn_type = "debit"

        # Validate counterparty
        counterparty = str(row.get("counterparty", "")).strip()
        if not counterparty:
            row_errors.append(f"Row {idx}: Missing counterparty")
            continue

        if row_errors:
            errors.extend(row_errors)
            continue

        # Build record
        record = {
            "transaction_id": txn_id,
            "date": date_parsed.isoformat(),
            "amount": abs(amount),  # Store as positive
            "currency": str(row.get("currency", "USD")).strip().upper() or "USD",
            "transaction_type": txn_type,
            "counterparty": counterparty,
            "counterparty_account": str(row.get("counterparty_account", "")).strip() or None,
            "country": str(row.get("country", "")).strip().upper() or None,
            "description": str(row.get("description", "")).strip() or None,
        }
        records.append(record)

    if not records:
        errors.append("No valid records found in file")

    return records, errors


def validate_kyc_data(data: Dict[str, Any]) -> Tuple[Dict[str, Any], List[str]]:
    """
    Validate KYC data dictionary.

    Returns tuple of (validated_data, error_messages).
    """
    errors = []

    # Required fields
    required_fields = ["customer_id", "name", "account_number", "account_type"]

    for field in required_fields:
        if field not in data or not data.get(field):
            errors.append(f"Missing required field: {field}")

    if errors:
        return {}, errors

    # Build validated KYC data
    validated = {
        "customer_id": str(data["customer_id"]).strip(),
        "name": str(data["name"]).strip(),
        "account_number": str(data["account_number"]).strip(),
        "account_type": str(data["account_type"]).strip(),
        "date_opened": data.get("date_opened"),
        "occupation": str(data.get("occupation", "")).strip() or None,
        "address": str(data.get("address", "")).strip() or None,
        "country": str(data.get("country", "US")).strip().upper(),
        "risk_rating": str(data.get("risk_rating", "")).strip() or None,
        "pep_status": bool(data.get("pep_status", False)),
        "sanctions_match": bool(data.get("sanctions_match", False)),
    }

    # Parse date_opened if provided
    if validated["date_opened"]:
        try:
            if isinstance(validated["date_opened"], str):
                validated["date_opened"] = pd.to_datetime(validated["date_opened"]).isoformat()
        except Exception:
            validated["date_opened"] = None

    return validated, errors


def validate_json_transactions(data: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], List[str]]:
    """
    Validate transactions from JSON format.

    Returns tuple of (valid_records, error_messages).
    """
    # Convert to DataFrame for consistent processing
    df = pd.DataFrame(data)
    return validate_transaction_dataframe(df)
