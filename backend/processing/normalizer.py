"""Data normalization utilities."""

from typing import List, Dict, Any
from datetime import datetime
import pandas as pd


def normalize_transactions_to_dataframe(transactions: List[Dict[str, Any]]) -> pd.DataFrame:
    """
    Convert transaction list to normalized DataFrame.

    Ensures consistent data types and formats.
    """
    if not transactions:
        return pd.DataFrame()

    df = pd.DataFrame(transactions)

    # Parse dates
    df["date"] = pd.to_datetime(df["date"])

    # Ensure numeric amounts
    df["amount"] = pd.to_numeric(df["amount"], errors="coerce").fillna(0)

    # Normalize transaction types
    df["transaction_type"] = df["transaction_type"].str.lower()

    # Add derived columns
    df["day_of_week"] = df["date"].dt.dayofweek  # 0=Monday, 6=Sunday
    df["hour"] = df["date"].dt.hour
    df["is_weekend"] = df["day_of_week"].isin([5, 6])
    df["is_off_hours"] = (df["hour"] < 8) | (df["hour"] > 18)

    # Flag cross-border (non-US)
    df["is_cross_border"] = df["country"].notna() & (df["country"] != "US")

    # Flag round amounts (divisible by 100 or 1000)
    df["is_round_amount"] = (
        (df["amount"] % 1000 == 0) |
        ((df["amount"] % 100 == 0) & (df["amount"] >= 1000))
    )

    return df


def normalize_currency_amounts(
    transactions: List[Dict[str, Any]],
    target_currency: str = "USD"
) -> List[Dict[str, Any]]:
    """
    Normalize all amounts to target currency.

    Note: In production, this would use real exchange rates.
    For demo purposes, assumes all amounts are already in USD equivalent.
    """
    # Simplified - just returns as-is
    # In production, would integrate with exchange rate API
    return transactions


def calculate_time_deltas(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calculate time differences between consecutive transactions.
    """
    if df.empty:
        return df

    df = df.sort_values("date")
    df["time_delta_hours"] = df["date"].diff().dt.total_seconds() / 3600
    df["time_delta_hours"] = df["time_delta_hours"].fillna(0)

    return df


def aggregate_by_counterparty(df: pd.DataFrame) -> pd.DataFrame:
    """
    Aggregate transactions by counterparty.
    """
    if df.empty:
        return pd.DataFrame()

    agg = df.groupby("counterparty").agg(
        total_amount=("amount", "sum"),
        transaction_count=("transaction_id", "count"),
        avg_amount=("amount", "mean"),
        first_transaction=("date", "min"),
        last_transaction=("date", "max"),
        countries=("country", lambda x: list(x.dropna().unique())),
    ).reset_index()

    return agg


def aggregate_by_date(df: pd.DataFrame) -> pd.DataFrame:
    """
    Aggregate transactions by date.
    """
    if df.empty:
        return pd.DataFrame()

    df["date_only"] = df["date"].dt.date

    agg = df.groupby("date_only").agg(
        total_amount=("amount", "sum"),
        transaction_count=("transaction_id", "count"),
        credit_amount=("amount", lambda x: x[df.loc[x.index, "transaction_type"] == "credit"].sum()),
        debit_amount=("amount", lambda x: x[df.loc[x.index, "transaction_type"] == "debit"].sum()),
    ).reset_index()

    return agg
