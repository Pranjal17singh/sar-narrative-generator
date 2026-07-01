"""Tests for pattern detection."""

import pytest

from backend.patterns.detector import detect_patterns
from backend.patterns.models import PatternType
from backend.processing.features import extract_features


@pytest.fixture
def structuring_transactions():
    """Transactions exhibiting structuring pattern."""
    return [
        {"transaction_id": f"TXN{i}", "date": f"2024-01-{5+i//3}T09:00:00",
         "amount": 9500 - (i * 100), "currency": "USD", "transaction_type": "credit",
         "counterparty": f"Party {i}", "country": "US"}
        for i in range(10)
    ]


@pytest.fixture
def funnel_transactions():
    """Transactions exhibiting funnel pattern."""
    # Multiple sources
    sources = [
        {"transaction_id": f"IN{i}", "date": f"2024-01-{5+i}T09:00:00",
         "amount": 5000 + (i * 1000), "currency": "USD", "transaction_type": "credit",
         "counterparty": f"Source {i}", "country": "US"}
        for i in range(5)
    ]
    # Single large outbound
    destination = [
        {"transaction_id": "OUT1", "date": "2024-01-12T14:00:00",
         "amount": 30000, "currency": "USD", "transaction_type": "debit",
         "counterparty": "Single Destination", "country": "KY"}
    ]
    return sources + destination


@pytest.fixture
def cross_border_transactions():
    """Transactions with high-risk jurisdictions."""
    return [
        {"transaction_id": "TXN1", "date": "2024-01-05T09:00:00",
         "amount": 50000, "currency": "USD", "transaction_type": "debit",
         "counterparty": "Offshore Corp", "country": "KY"},
        {"transaction_id": "TXN2", "date": "2024-01-06T09:00:00",
         "amount": 25000, "currency": "USD", "transaction_type": "debit",
         "counterparty": "Shell Co", "country": "VG"},
        {"transaction_id": "TXN3", "date": "2024-01-04T09:00:00",
         "amount": 100000, "currency": "USD", "transaction_type": "credit",
         "counterparty": "Client", "country": "US"},
    ]


def test_detect_structuring(structuring_transactions):
    """Test structuring pattern detection."""
    features = extract_features(structuring_transactions)
    patterns = detect_patterns(structuring_transactions, features)

    pattern_types = [p.pattern_type for p in patterns]
    assert PatternType.STRUCTURING in pattern_types

    structuring = next(p for p in patterns if p.pattern_type == PatternType.STRUCTURING)
    assert structuring.confidence > 0.5
    assert structuring.severity in ["medium", "high", "critical"]


def test_detect_funnel(funnel_transactions):
    """Test funnel activity detection."""
    features = extract_features(funnel_transactions)
    patterns = detect_patterns(funnel_transactions, features)

    pattern_types = [p.pattern_type for p in patterns]
    assert PatternType.FUNNEL in pattern_types

    funnel = next(p for p in patterns if p.pattern_type == PatternType.FUNNEL)
    assert "Single Destination" in funnel.description


def test_detect_cross_border(cross_border_transactions):
    """Test cross-border anomaly detection."""
    features = extract_features(cross_border_transactions)
    patterns = detect_patterns(cross_border_transactions, features)

    pattern_types = [p.pattern_type for p in patterns]
    assert PatternType.CROSS_BORDER in pattern_types

    cb = next(p for p in patterns if p.pattern_type == PatternType.CROSS_BORDER)
    assert "KY" in cb.description or "VG" in cb.description


def test_no_patterns_clean_transactions():
    """Test that clean transactions don't trigger patterns."""
    clean_txns = [
        {"transaction_id": "TXN1", "date": "2024-01-05T09:00:00",
         "amount": 1500, "currency": "USD", "transaction_type": "credit",
         "counterparty": "Regular Client", "country": "US"},
        {"transaction_id": "TXN2", "date": "2024-01-06T09:00:00",
         "amount": 1200, "currency": "USD", "transaction_type": "debit",
         "counterparty": "Vendor", "country": "US"},
    ]

    features = extract_features(clean_txns)
    patterns = detect_patterns(clean_txns, features)

    # Clean transactions shouldn't trigger structuring or major patterns
    pattern_types = [p.pattern_type for p in patterns]
    assert PatternType.STRUCTURING not in pattern_types


def test_pattern_evidence():
    """Test that patterns include evidence."""
    txns = [
        {"transaction_id": f"TXN{i}", "date": f"2024-01-05T0{9+i}:00:00",
         "amount": 9900, "currency": "USD", "transaction_type": "credit",
         "counterparty": f"Party {i}", "country": "US"}
        for i in range(5)
    ]

    features = extract_features(txns)
    patterns = detect_patterns(txns, features)

    for pattern in patterns:
        assert hasattr(pattern, "evidence")
        assert hasattr(pattern, "affected_transactions")
