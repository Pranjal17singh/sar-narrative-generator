"""Tests for feature extraction."""

import pytest
from datetime import datetime

from backend.processing.features import extract_features


@pytest.fixture
def sample_transactions():
    """Sample transaction data for testing."""
    return [
        {
            "transaction_id": "TXN001",
            "date": "2024-01-05T09:15:00",
            "amount": 9500.00,
            "currency": "USD",
            "transaction_type": "credit",
            "counterparty": "ABC Corp",
            "country": "US",
        },
        {
            "transaction_id": "TXN002",
            "date": "2024-01-05T10:00:00",
            "amount": 9400.00,
            "currency": "USD",
            "transaction_type": "credit",
            "counterparty": "XYZ LLC",
            "country": "US",
        },
        {
            "transaction_id": "TXN003",
            "date": "2024-01-05T14:00:00",
            "amount": 15000.00,
            "currency": "USD",
            "transaction_type": "debit",
            "counterparty": "Offshore Ltd",
            "country": "KY",
        },
        {
            "transaction_id": "TXN004",
            "date": "2024-01-06T09:00:00",
            "amount": 10000.00,
            "currency": "USD",
            "transaction_type": "credit",
            "counterparty": "Round Amount Inc",
            "country": "US",
        },
    ]


def test_extract_features_basic(sample_transactions):
    """Test basic feature extraction."""
    features = extract_features(sample_transactions)

    assert features["transaction_count"] == 4
    assert features["total_inflow"] == 28900.00  # 9500 + 9400 + 10000
    assert features["total_outflow"] == 15000.00
    assert features["net_flow"] == 13900.00


def test_extract_features_counterparties(sample_transactions):
    """Test counterparty counting."""
    features = extract_features(sample_transactions)

    assert features["unique_counterparties"] == 4


def test_extract_features_cross_border(sample_transactions):
    """Test cross-border detection."""
    features = extract_features(sample_transactions)

    assert features["cross_border_count"] == 1
    assert "KY" in features["cross_border_countries"]


def test_extract_features_round_amounts(sample_transactions):
    """Test round amount detection."""
    features = extract_features(sample_transactions)

    assert features["round_amount_count"] >= 1


def test_extract_features_empty():
    """Test handling of empty transaction list."""
    features = extract_features([])
    assert features == {}


def test_extract_features_amount_stats(sample_transactions):
    """Test amount statistics."""
    features = extract_features(sample_transactions)

    assert features["max_transaction_amount"] == 15000.00
    assert features["min_transaction_amount"] == 9400.00
    assert features["avg_transaction_amount"] > 0
