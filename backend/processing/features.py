"""Feature extraction engine for transaction analysis."""

from typing import List, Dict, Any
from datetime import datetime
import pandas as pd

from backend.processing.normalizer import (
    normalize_transactions_to_dataframe,
    calculate_time_deltas,
    aggregate_by_counterparty,
)


def extract_features(transactions: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Extract analytical features from transaction data.

    Returns comprehensive feature dictionary for pattern detection and narrative generation.
    """
    if not transactions:
        return {}

    # Normalize to DataFrame
    df = normalize_transactions_to_dataframe(transactions)
    df = calculate_time_deltas(df)

    # Separate credits and debits
    credits = df[df["transaction_type"] == "credit"]
    debits = df[df["transaction_type"] == "debit"]

    # Basic aggregations
    total_inflow = float(credits["amount"].sum())
    total_outflow = float(debits["amount"].sum())

    # Date range
    date_min = df["date"].min()
    date_max = df["date"].max()
    date_range_days = (date_max - date_min).days + 1 if len(df) > 1 else 1

    # Counterparty analysis
    counterparty_agg = aggregate_by_counterparty(df)
    unique_counterparties = len(counterparty_agg)

    # Cross-border analysis
    cross_border_df = df[df["is_cross_border"]]
    cross_border_count = len(cross_border_df)
    cross_border_amount = float(cross_border_df["amount"].sum())
    cross_border_countries = list(cross_border_df["country"].unique()) if not cross_border_df.empty else []

    # Time-based patterns
    weekend_txns = df[df["is_weekend"]]
    off_hours_txns = df[df["is_off_hours"]]

    # Round amount analysis
    round_amount_df = df[df["is_round_amount"]]

    # Velocity calculations
    transactions_per_day = len(df) / date_range_days if date_range_days > 0 else 0

    # Amount statistics
    amounts = df["amount"]

    # Rapid movement detection (transactions within 24 hours)
    rapid_pairs = []
    df_sorted = df.sort_values("date")
    for i, row in df_sorted.iterrows():
        if row["transaction_type"] == "credit":
            # Look for debits within 24 hours
            window_start = row["date"]
            window_end = row["date"] + pd.Timedelta(hours=24)
            matching_debits = df_sorted[
                (df_sorted["transaction_type"] == "debit") &
                (df_sorted["date"] > window_start) &
                (df_sorted["date"] <= window_end)
            ]
            if not matching_debits.empty:
                rapid_pairs.append({
                    "credit_id": row["transaction_id"],
                    "credit_amount": row["amount"],
                    "debit_ids": matching_debits["transaction_id"].tolist(),
                    "debit_amount": matching_debits["amount"].sum(),
                })

    # Structuring detection (amounts just below $10,000 CTR threshold)
    structuring_threshold = 10000
    near_threshold_df = df[
        (df["amount"] >= structuring_threshold * 0.9) &
        (df["amount"] < structuring_threshold)
    ]

    # Build feature dictionary
    features = {
        # Volume metrics
        "total_inflow": total_inflow,
        "total_outflow": total_outflow,
        "net_flow": total_inflow - total_outflow,
        "transaction_count": len(df),
        "credit_count": len(credits),
        "debit_count": len(debits),

        # Counterparty metrics
        "unique_counterparties": unique_counterparties,
        "inbound_counterparties": len(credits["counterparty"].unique()),
        "outbound_counterparties": len(debits["counterparty"].unique()),

        # Cross-border metrics
        "cross_border_count": cross_border_count,
        "cross_border_amount": cross_border_amount,
        "cross_border_percentage": (cross_border_count / len(df) * 100) if len(df) > 0 else 0,
        "cross_border_countries": cross_border_countries,

        # Amount statistics
        "avg_transaction_amount": float(amounts.mean()) if len(amounts) > 0 else 0,
        "max_transaction_amount": float(amounts.max()) if len(amounts) > 0 else 0,
        "min_transaction_amount": float(amounts.min()) if len(amounts) > 0 else 0,
        "median_transaction_amount": float(amounts.median()) if len(amounts) > 0 else 0,
        "std_transaction_amount": float(amounts.std()) if len(amounts) > 1 else 0,

        # Time-based metrics
        "date_range_days": date_range_days,
        "transactions_per_day": round(transactions_per_day, 2),
        "weekend_transaction_count": len(weekend_txns),
        "weekend_percentage": (len(weekend_txns) / len(df) * 100) if len(df) > 0 else 0,
        "off_hours_transaction_count": len(off_hours_txns),
        "off_hours_percentage": (len(off_hours_txns) / len(df) * 100) if len(df) > 0 else 0,

        # Pattern indicators
        "round_amount_count": len(round_amount_df),
        "round_amount_percentage": (len(round_amount_df) / len(df) * 100) if len(df) > 0 else 0,
        "near_threshold_count": len(near_threshold_df),
        "rapid_movement_pairs": len(rapid_pairs),

        # Currency
        "currency_count": df["currency"].nunique() if "currency" in df.columns else 1,
        "currencies": list(df["currency"].unique()) if "currency" in df.columns else ["USD"],

        # Date info
        "first_transaction_date": date_min.isoformat() if pd.notna(date_min) else None,
        "last_transaction_date": date_max.isoformat() if pd.notna(date_max) else None,

        # Top counterparties by volume
        "top_counterparties": _get_top_counterparties(counterparty_agg, 5),

        # Rapid movement details
        "rapid_movement_details": rapid_pairs[:10],  # Limit to first 10

        # Near-threshold transactions
        "near_threshold_transactions": near_threshold_df["transaction_id"].tolist()[:20],
    }

    return features


def _get_top_counterparties(agg_df: pd.DataFrame, n: int = 5) -> List[Dict[str, Any]]:
    """Get top N counterparties by total amount."""
    if agg_df.empty:
        return []

    top = agg_df.nlargest(n, "total_amount")
    return [
        {
            "counterparty": row["counterparty"],
            "total_amount": float(row["total_amount"]),
            "transaction_count": int(row["transaction_count"]),
        }
        for _, row in top.iterrows()
    ]


def calculate_velocity_metrics(
    transactions: List[Dict[str, Any]],
    window_days: int = 7
) -> Dict[str, Any]:
    """
    Calculate transaction velocity over time windows.

    Useful for detecting sudden spikes in activity.
    """
    if not transactions:
        return {}

    df = normalize_transactions_to_dataframe(transactions)
    df["date_only"] = df["date"].dt.date

    daily_counts = df.groupby("date_only").size()
    daily_amounts = df.groupby("date_only")["amount"].sum()

    # Calculate rolling averages
    if len(daily_counts) >= window_days:
        rolling_count_avg = daily_counts.rolling(window=window_days).mean()
        rolling_amount_avg = daily_amounts.rolling(window=window_days).mean()

        # Find spikes (days with 3x+ the average)
        count_spikes = daily_counts[daily_counts > rolling_count_avg * 3].index.tolist()
        amount_spikes = daily_amounts[daily_amounts > rolling_amount_avg * 3].index.tolist()
    else:
        count_spikes = []
        amount_spikes = []

    return {
        "daily_transaction_counts": {str(k): int(v) for k, v in daily_counts.items()},
        "daily_amounts": {str(k): float(v) for k, v in daily_amounts.items()},
        "count_spike_dates": [str(d) for d in count_spikes],
        "amount_spike_dates": [str(d) for d in amount_spikes],
        "avg_daily_transactions": float(daily_counts.mean()),
        "max_daily_transactions": int(daily_counts.max()),
        "avg_daily_amount": float(daily_amounts.mean()),
        "max_daily_amount": float(daily_amounts.max()),
    }
