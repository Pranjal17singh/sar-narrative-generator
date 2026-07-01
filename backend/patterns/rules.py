"""Pattern detection rule definitions."""

from typing import List, Dict, Any
from dataclasses import dataclass
from enum import Enum


@dataclass
class RuleThreshold:
    """Thresholds for pattern detection rules."""
    # Structuring
    ctr_threshold: float = 10000.0
    structuring_lower_bound: float = 0.8  # 80% of CTR threshold
    structuring_min_count: int = 3  # Minimum transactions to flag

    # Funnel activity
    funnel_min_sources: int = 3  # Minimum inbound sources
    funnel_concentration_threshold: float = 0.7  # 70% going to single destination

    # Rapid movement
    rapid_movement_hours: int = 24  # Hours between in/out
    rapid_movement_percentage: float = 0.8  # 80% of inflow moved out

    # Velocity spike
    velocity_spike_multiplier: float = 3.0  # 3x normal activity
    velocity_min_baseline_days: int = 7  # Days needed for baseline

    # Round amounts
    round_amount_threshold: float = 100.0  # Divisible by this
    round_amount_min_percentage: float = 0.3  # 30% of transactions

    # Cross-border
    cross_border_high_risk_percentage: float = 0.5  # 50%+ to high-risk jurisdictions


# High-risk jurisdictions for AML purposes
HIGH_RISK_JURISDICTIONS = [
    "AF",  # Afghanistan
    "BY",  # Belarus
    "MM",  # Myanmar
    "KP",  # North Korea
    "IR",  # Iran
    "IQ",  # Iraq
    "LY",  # Libya
    "ML",  # Mali
    "NI",  # Nicaragua
    "PK",  # Pakistan
    "PA",  # Panama
    "RU",  # Russia
    "SO",  # Somalia
    "SS",  # South Sudan
    "SD",  # Sudan
    "SY",  # Syria
    "VE",  # Venezuela
    "YE",  # Yemen
    "ZW",  # Zimbabwe
    # Offshore jurisdictions often associated with shell companies
    "VG",  # British Virgin Islands
    "KY",  # Cayman Islands
    "BZ",  # Belize
    "SC",  # Seychelles
    "MH",  # Marshall Islands
]

# Pattern descriptions for narrative generation
PATTERN_DESCRIPTIONS = {
    "funnel": {
        "name": "Funnel Activity",
        "description": "Multiple sources of funds concentrated into a single or few outbound destinations",
        "typology": "Layering technique commonly used in money laundering to obscure the source of funds",
        "indicators": [
            "Multiple incoming transfers from different parties",
            "Single or limited outbound destinations",
            "Little time between receipt and transfer",
        ],
    },
    "rapid_movement": {
        "name": "Rapid Movement of Funds",
        "description": "Funds moved quickly through the account with minimal retention",
        "typology": "Pass-through activity suggesting account used as conduit",
        "indicators": [
            "Large deposits followed by rapid withdrawals",
            "Minimal account balance maintenance",
            "No apparent business purpose for transactions",
        ],
    },
    "structuring": {
        "name": "Structuring/Smurfing",
        "description": "Multiple transactions structured to avoid Currency Transaction Report (CTR) requirements",
        "typology": "Breaking up transactions to stay below $10,000 reporting threshold",
        "indicators": [
            "Multiple transactions just below $10,000",
            "Transactions occurring in close succession",
            "No legitimate business explanation",
        ],
    },
    "cross_border": {
        "name": "Cross-Border Anomalies",
        "description": "Unusual international transaction patterns involving high-risk jurisdictions",
        "typology": "Movement of funds to/from countries with weak AML controls",
        "indicators": [
            "Transactions with high-risk jurisdictions",
            "Offshore financial centers involvement",
            "Inconsistent with stated business purpose",
        ],
    },
    "round_amounts": {
        "name": "Round Amount Pattern",
        "description": "High frequency of round-number transactions suggesting artificial structuring",
        "typology": "Unusual pattern inconsistent with normal business activity",
        "indicators": [
            "Multiple transactions in round amounts",
            "Amounts like $5,000, $10,000, $25,000",
            "Lack of cents or irregular amounts",
        ],
    },
    "velocity_spike": {
        "name": "Velocity Spike",
        "description": "Sudden increase in transaction frequency or volume",
        "typology": "Abnormal activity suggesting burst of suspicious transfers",
        "indicators": [
            "Transaction count significantly above baseline",
            "Transaction volume significantly above baseline",
            "Activity inconsistent with historical patterns",
        ],
    },
}


def get_pattern_description(pattern_type: str) -> Dict[str, Any]:
    """Get detailed description for a pattern type."""
    return PATTERN_DESCRIPTIONS.get(pattern_type, {
        "name": pattern_type.replace("_", " ").title(),
        "description": "Suspicious pattern detected",
        "typology": "Unknown",
        "indicators": [],
    })
