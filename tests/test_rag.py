"""Tests for RAG system."""

import pytest

from backend.rag.embeddings import (
    chunk_text,
    prepare_case_context_for_embedding,
)
from backend.rag.retriever import (
    get_fallback_context,
    format_customer_info,
    format_transaction_summary,
    format_patterns_for_prompt,
)


def test_chunk_text_short():
    """Test chunking of short text."""
    short_text = "This is a short text."
    chunks = chunk_text(short_text, chunk_size=500)

    assert len(chunks) == 1
    assert chunks[0] == short_text


def test_chunk_text_long():
    """Test chunking of long text."""
    long_text = "This is a sentence. " * 100
    chunks = chunk_text(long_text, chunk_size=100, overlap=20)

    assert len(chunks) > 1
    # Check overlap exists
    for i in range(len(chunks) - 1):
        # Some content should overlap between chunks
        assert len(chunks[i]) <= 100 + 50  # Allow for sentence boundary adjustment


def test_prepare_case_context():
    """Test case context preparation for embedding."""
    kyc = {"name": "Test Corp", "account_type": "Business", "country": "US"}
    features = {
        "total_inflow": 100000,
        "total_outflow": 50000,
        "transaction_count": 20,
        "cross_border_countries": ["UK", "DE"],
    }
    patterns = [{"pattern_type": "structuring"}, {"pattern_type": "funnel"}]

    context = prepare_case_context_for_embedding(kyc, features, patterns)

    assert "Test Corp" in context
    assert "Business" in context
    assert "structuring" in context
    assert "funnel" in context


def test_get_fallback_context():
    """Test fallback context availability."""
    context = get_fallback_context()

    assert context is not None
    assert len(context) > 100
    assert "SAR" in context or "narrative" in context.lower()


def test_format_customer_info():
    """Test KYC formatting."""
    kyc = {
        "name": "Acme Inc",
        "customer_id": "CUST001",
        "account_number": "ACC123",
        "account_type": "Checking",
        "country": "US",
        "occupation": "Trading",
        "risk_rating": "High",
    }

    formatted = format_customer_info(kyc)

    assert "Acme Inc" in formatted
    assert "CUST001" in formatted
    assert "ACC123" in formatted
    assert "High" in formatted


def test_format_customer_info_empty():
    """Test KYC formatting with empty data."""
    formatted = format_customer_info({})
    assert "not available" in formatted.lower()


def test_format_transaction_summary():
    """Test transaction summary formatting."""
    features = {
        "transaction_count": 50,
        "total_inflow": 500000,
        "total_outflow": 450000,
        "net_flow": 50000,
        "unique_counterparties": 15,
        "cross_border_count": 5,
        "cross_border_countries": ["UK", "DE", "CH"],
        "first_transaction_date": "2024-01-01",
        "last_transaction_date": "2024-01-31",
    }

    formatted = format_transaction_summary(features)

    assert "50" in formatted  # transaction count
    assert "500,000" in formatted  # inflow
    assert "UK" in formatted or "DE" in formatted


def test_format_patterns_for_prompt():
    """Test pattern formatting for prompt."""
    patterns = [
        {
            "pattern_type": "structuring",
            "confidence": 0.85,
            "severity": "high",
            "description": "Multiple transactions below threshold",
            "recommendation": "Review for CTR avoidance",
        }
    ]
    pattern_descs = [
        {
            "name": "Structuring",
            "typology": "Breaking up transactions",
        }
    ]

    formatted = format_patterns_for_prompt(patterns, pattern_descs)

    assert "Structuring" in formatted
    assert "85%" in formatted
    assert "HIGH" in formatted
