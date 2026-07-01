"""Rule-based pattern detection engine."""

from typing import List, Dict, Any
import pandas as pd

from backend.patterns.models import PatternMatch, PatternType, Severity
from backend.patterns.rules import (
    RuleThreshold,
    HIGH_RISK_JURISDICTIONS,
    get_pattern_description,
)
from backend.processing.normalizer import normalize_transactions_to_dataframe


def detect_patterns(
    transactions: List[Dict[str, Any]],
    features: Dict[str, Any],
    thresholds: RuleThreshold = None,
) -> List[PatternMatch]:
    """
    Detect suspicious patterns in transaction data.

    Args:
        transactions: List of transaction records
        features: Pre-extracted features
        thresholds: Optional custom thresholds

    Returns:
        List of detected patterns with confidence scores
    """
    if not transactions or not features:
        return []

    thresholds = thresholds or RuleThreshold()
    patterns = []

    # Convert to DataFrame for analysis
    df = normalize_transactions_to_dataframe(transactions)

    # Run each detection rule
    structuring = detect_structuring(df, features, thresholds)
    if structuring:
        patterns.append(structuring)

    funnel = detect_funnel_activity(df, features, thresholds)
    if funnel:
        patterns.append(funnel)

    rapid = detect_rapid_movement(df, features, thresholds)
    if rapid:
        patterns.append(rapid)

    cross_border = detect_cross_border_anomalies(df, features, thresholds)
    if cross_border:
        patterns.append(cross_border)

    round_amounts = detect_round_amounts(df, features, thresholds)
    if round_amounts:
        patterns.append(round_amounts)

    velocity = detect_velocity_spike(df, features, thresholds)
    if velocity:
        patterns.append(velocity)

    return patterns


def detect_structuring(
    df: pd.DataFrame,
    features: Dict[str, Any],
    thresholds: RuleThreshold,
) -> PatternMatch | None:
    """Detect structuring/smurfing patterns."""
    ctr = thresholds.ctr_threshold
    lower = ctr * thresholds.structuring_lower_bound

    # Find transactions in structuring range
    structuring_df = df[
        (df["amount"] >= lower) &
        (df["amount"] < ctr) &
        (df["transaction_type"] == "credit")
    ]

    if len(structuring_df) < thresholds.structuring_min_count:
        return None

    # Calculate confidence based on count and proximity to threshold
    count = len(structuring_df)
    avg_amount = structuring_df["amount"].mean()
    proximity = (avg_amount - lower) / (ctr - lower)  # How close to $10k

    # Higher confidence if amounts cluster just below threshold
    confidence = min(0.95, 0.5 + (count / 10) * 0.3 + proximity * 0.2)

    # Severity based on count
    if count >= 10:
        severity = Severity.CRITICAL
    elif count >= 5:
        severity = Severity.HIGH
    else:
        severity = Severity.MEDIUM

    desc = get_pattern_description("structuring")

    return PatternMatch(
        pattern_type=PatternType.STRUCTURING,
        confidence=round(confidence, 2),
        severity=severity,
        description=f"{count} transactions detected between ${lower:,.0f} and ${ctr:,.0f}, "
                    f"averaging ${avg_amount:,.2f}. {desc['typology']}",
        evidence=[
            {
                "transaction_id": row["transaction_id"],
                "amount": row["amount"],
                "date": row["date"].isoformat(),
            }
            for _, row in structuring_df.iterrows()
        ],
        affected_transactions=structuring_df["transaction_id"].tolist(),
        recommendation="Review for potential Currency Transaction Report avoidance",
    )


def detect_funnel_activity(
    df: pd.DataFrame,
    features: Dict[str, Any],
    thresholds: RuleThreshold,
) -> PatternMatch | None:
    """Detect funnel activity - multiple sources to single destination."""
    credits = df[df["transaction_type"] == "credit"]
    debits = df[df["transaction_type"] == "debit"]

    if len(credits) < thresholds.funnel_min_sources or len(debits) == 0:
        return None

    # Count unique inbound sources
    inbound_sources = credits["counterparty"].nunique()

    # Check outbound concentration
    outbound_totals = debits.groupby("counterparty")["amount"].sum()
    total_outbound = outbound_totals.sum()

    if total_outbound == 0:
        return None

    max_outbound_party = outbound_totals.max()
    concentration = max_outbound_party / total_outbound

    if inbound_sources < thresholds.funnel_min_sources:
        return None

    if concentration < thresholds.funnel_concentration_threshold:
        return None

    # Calculate confidence
    confidence = min(0.95, 0.5 + (inbound_sources / 10) * 0.3 + concentration * 0.2)

    # Severity based on amounts involved
    if total_outbound >= 100000:
        severity = Severity.CRITICAL
    elif total_outbound >= 50000:
        severity = Severity.HIGH
    else:
        severity = Severity.MEDIUM

    top_destination = outbound_totals.idxmax()
    desc = get_pattern_description("funnel")

    return PatternMatch(
        pattern_type=PatternType.FUNNEL,
        confidence=round(confidence, 2),
        severity=severity,
        description=f"Funds from {inbound_sources} different sources concentrated with "
                    f"{concentration*100:.1f}% going to {top_destination}. {desc['typology']}",
        evidence=[
            {"inbound_sources": inbound_sources},
            {"top_destination": top_destination},
            {"concentration_percentage": round(concentration * 100, 1)},
            {"total_outbound": total_outbound},
        ],
        affected_transactions=debits[debits["counterparty"] == top_destination]["transaction_id"].tolist(),
        recommendation="Investigate relationship between inbound parties and outbound destination",
    )


def detect_rapid_movement(
    df: pd.DataFrame,
    features: Dict[str, Any],
    thresholds: RuleThreshold,
) -> PatternMatch | None:
    """Detect rapid movement - funds quickly passing through account."""
    rapid_pairs = features.get("rapid_movement_details", [])

    if not rapid_pairs:
        return None

    # Calculate total rapid movement
    total_rapid = sum(p.get("debit_amount", 0) for p in rapid_pairs)
    total_inflow = features.get("total_inflow", 0)

    if total_inflow == 0:
        return None

    rapid_percentage = total_rapid / total_inflow

    if rapid_percentage < thresholds.rapid_movement_percentage * 0.5:  # At least 40%
        return None

    confidence = min(0.95, 0.5 + rapid_percentage * 0.4 + len(rapid_pairs) / 10 * 0.1)

    if rapid_percentage >= 0.9:
        severity = Severity.CRITICAL
    elif rapid_percentage >= 0.7:
        severity = Severity.HIGH
    else:
        severity = Severity.MEDIUM

    desc = get_pattern_description("rapid_movement")

    return PatternMatch(
        pattern_type=PatternType.RAPID_MOVEMENT,
        confidence=round(confidence, 2),
        severity=severity,
        description=f"{len(rapid_pairs)} instances of funds ({rapid_percentage*100:.1f}% of inflow) "
                    f"moved within {thresholds.rapid_movement_hours} hours of receipt. {desc['typology']}",
        evidence=rapid_pairs[:5],  # Top 5 examples
        affected_transactions=[
            txn_id
            for p in rapid_pairs
            for txn_id in [p.get("credit_id")] + p.get("debit_ids", [])
            if txn_id
        ][:20],
        recommendation="Review for pass-through/conduit activity",
    )


def detect_cross_border_anomalies(
    df: pd.DataFrame,
    features: Dict[str, Any],
    thresholds: RuleThreshold,
) -> PatternMatch | None:
    """Detect suspicious cross-border activity."""
    cross_border_countries = features.get("cross_border_countries", [])

    if not cross_border_countries:
        return None

    # Check for high-risk jurisdictions
    high_risk_found = [c for c in cross_border_countries if c in HIGH_RISK_JURISDICTIONS]

    cross_border_df = df[df["is_cross_border"]]
    high_risk_df = cross_border_df[cross_border_df["country"].isin(HIGH_RISK_JURISDICTIONS)]

    total_cross_border = cross_border_df["amount"].sum()
    high_risk_amount = high_risk_df["amount"].sum()

    if not high_risk_found and features.get("cross_border_percentage", 0) < 30:
        return None

    # Calculate confidence
    confidence = 0.5
    if high_risk_found:
        confidence += 0.3
    if high_risk_amount > 50000:
        confidence += 0.1
    if len(high_risk_df) > 5:
        confidence += 0.1
    confidence = min(0.95, confidence)

    if high_risk_amount >= 100000 or len(high_risk_found) >= 3:
        severity = Severity.CRITICAL
    elif high_risk_amount >= 50000 or len(high_risk_found) >= 2:
        severity = Severity.HIGH
    else:
        severity = Severity.MEDIUM

    desc = get_pattern_description("cross_border")

    return PatternMatch(
        pattern_type=PatternType.CROSS_BORDER,
        confidence=round(confidence, 2),
        severity=severity,
        description=f"Cross-border activity involving {len(cross_border_countries)} countries. "
                    f"High-risk jurisdictions: {', '.join(high_risk_found) or 'None'}. "
                    f"Total cross-border: ${total_cross_border:,.2f}. {desc['typology']}",
        evidence=[
            {"high_risk_jurisdictions": high_risk_found},
            {"all_countries": cross_border_countries},
            {"high_risk_amount": high_risk_amount},
            {"total_cross_border": total_cross_border},
        ],
        affected_transactions=cross_border_df["transaction_id"].tolist(),
        recommendation="Review business purpose for international transactions",
    )


def detect_round_amounts(
    df: pd.DataFrame,
    features: Dict[str, Any],
    thresholds: RuleThreshold,
) -> PatternMatch | None:
    """Detect unusual frequency of round-amount transactions."""
    round_percentage = features.get("round_amount_percentage", 0) / 100
    round_count = features.get("round_amount_count", 0)

    if round_percentage < thresholds.round_amount_min_percentage:
        return None

    round_df = df[df["is_round_amount"]]
    round_amounts_list = round_df["amount"].tolist()

    confidence = min(0.9, 0.4 + round_percentage * 0.5)

    if round_percentage >= 0.6:
        severity = Severity.HIGH
    elif round_percentage >= 0.4:
        severity = Severity.MEDIUM
    else:
        severity = Severity.LOW

    desc = get_pattern_description("round_amounts")

    return PatternMatch(
        pattern_type=PatternType.ROUND_AMOUNTS,
        confidence=round(confidence, 2),
        severity=severity,
        description=f"{round_count} transactions ({round_percentage*100:.1f}%) are round amounts, "
                    f"including amounts like ${max(round_amounts_list):,.0f}. {desc['typology']}",
        evidence=[
            {"round_amount_count": round_count},
            {"round_percentage": round(round_percentage * 100, 1)},
            {"sample_amounts": sorted(set(round_amounts_list))[:10]},
        ],
        affected_transactions=round_df["transaction_id"].tolist(),
        recommendation="Assess whether round amounts are consistent with business operations",
    )


def detect_velocity_spike(
    df: pd.DataFrame,
    features: Dict[str, Any],
    thresholds: RuleThreshold,
) -> PatternMatch | None:
    """Detect sudden spikes in transaction velocity."""
    date_range = features.get("date_range_days", 0)

    if date_range < thresholds.velocity_min_baseline_days:
        return None

    # Calculate daily metrics
    df["date_only"] = df["date"].dt.date
    daily_counts = df.groupby("date_only").size()
    daily_amounts = df.groupby("date_only")["amount"].sum()

    if len(daily_counts) < 3:
        return None

    # Calculate baseline (average excluding max day)
    sorted_counts = daily_counts.sort_values()
    baseline_count = sorted_counts.iloc[:-1].mean() if len(sorted_counts) > 1 else sorted_counts.mean()
    max_count = daily_counts.max()

    baseline_amount = sorted_counts.iloc[:-1].mean() if len(sorted_counts) > 1 else daily_amounts.mean()
    max_amount = daily_amounts.max()

    # Check for spikes
    count_spike = max_count > baseline_count * thresholds.velocity_spike_multiplier
    amount_spike = max_amount > baseline_amount * thresholds.velocity_spike_multiplier

    if not (count_spike or amount_spike):
        return None

    spike_factor = max(
        max_count / baseline_count if baseline_count > 0 else 0,
        max_amount / baseline_amount if baseline_amount > 0 else 0,
    )

    confidence = min(0.9, 0.5 + (spike_factor - 3) / 10)

    if spike_factor >= 10:
        severity = Severity.CRITICAL
    elif spike_factor >= 5:
        severity = Severity.HIGH
    else:
        severity = Severity.MEDIUM

    spike_date = daily_counts.idxmax()
    desc = get_pattern_description("velocity_spike")

    return PatternMatch(
        pattern_type=PatternType.VELOCITY_SPIKE,
        confidence=round(confidence, 2),
        severity=severity,
        description=f"Activity spike of {spike_factor:.1f}x baseline detected on {spike_date}. "
                    f"Peak: {max_count} transactions vs baseline of {baseline_count:.1f}. {desc['typology']}",
        evidence=[
            {"spike_date": str(spike_date)},
            {"peak_transaction_count": int(max_count)},
            {"baseline_count": round(baseline_count, 1)},
            {"spike_factor": round(spike_factor, 1)},
        ],
        affected_transactions=df[df["date_only"] == spike_date]["transaction_id"].tolist(),
        recommendation="Review transactions on spike date for anomalies",
    )
