"""Tests for API endpoints."""

import pytest
from fastapi.testclient import TestClient
import json
import io

from backend.main import app
from backend.database import Base, engine


@pytest.fixture(autouse=True)
def setup_database():
    """Setup and teardown database for each test."""
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client():
    """Test client fixture."""
    return TestClient(app)


def test_root_endpoint(client):
    """Test root endpoint."""
    response = client.get("/")

    assert response.status_code == 200
    data = response.json()
    assert "name" in data
    assert "status" in data


def test_health_endpoint(client):
    """Test health check endpoint."""
    response = client.get("/health")

    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert "ollama_available" in data


def test_create_case(client):
    """Test case creation."""
    response = client.post(
        "/api/cases",
        json={"name": "Test Case 001"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Test Case 001"
    assert "id" in data
    assert data["status"] == "pending"


def test_list_cases(client):
    """Test listing cases."""
    # Create a case first
    client.post("/api/cases", json={"name": "Test Case"})

    response = client.get("/api/cases")

    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 1


def test_get_case(client):
    """Test getting case details."""
    # Create a case
    create_response = client.post("/api/cases", json={"name": "Detail Test"})
    case_id = create_response.json()["id"]

    response = client.get(f"/api/cases/{case_id}")

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == case_id
    assert data["name"] == "Detail Test"


def test_get_case_not_found(client):
    """Test getting non-existent case."""
    response = client.get("/api/cases/nonexistent-id")

    assert response.status_code == 404


def test_delete_case(client):
    """Test case deletion."""
    # Create a case
    create_response = client.post("/api/cases", json={"name": "Delete Test"})
    case_id = create_response.json()["id"]

    # Delete it
    response = client.delete(f"/api/cases/{case_id}")

    assert response.status_code == 200

    # Verify it's gone
    get_response = client.get(f"/api/cases/{case_id}")
    assert get_response.status_code == 404


def test_upload_transactions(client):
    """Test transaction file upload."""
    # Create a case
    create_response = client.post("/api/cases", json={"name": "Upload Test"})
    case_id = create_response.json()["id"]

    # Create CSV content
    csv_content = """transaction_id,date,amount,transaction_type,counterparty,country
TXN001,2024-01-05,9500,credit,ABC Corp,US
TXN002,2024-01-06,9400,credit,XYZ LLC,US
"""
    file = io.BytesIO(csv_content.encode())

    response = client.post(
        f"/api/upload/transactions/{case_id}",
        files={"file": ("transactions.csv", file, "text/csv")},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["records_processed"] == 2


def test_upload_kyc(client):
    """Test KYC file upload."""
    # Create a case
    create_response = client.post("/api/cases", json={"name": "KYC Test"})
    case_id = create_response.json()["id"]

    # Create JSON content
    kyc_data = {
        "customer_id": "CUST001",
        "name": "Test Customer",
        "account_number": "ACC123",
        "account_type": "Business",
    }
    file = io.BytesIO(json.dumps(kyc_data).encode())

    response = client.post(
        f"/api/upload/kyc/{case_id}",
        files={"file": ("kyc.json", file, "application/json")},
    )

    assert response.status_code == 200


def test_generate_narrative(client):
    """Test narrative generation."""
    # Create and populate a case
    create_response = client.post("/api/cases", json={"name": "Narrative Test"})
    case_id = create_response.json()["id"]

    # Upload transactions
    csv_content = """transaction_id,date,amount,transaction_type,counterparty,country
TXN001,2024-01-05,9500,credit,ABC Corp,US
TXN002,2024-01-06,9400,credit,XYZ LLC,US
TXN003,2024-01-07,15000,debit,Offshore Ltd,KY
"""
    file = io.BytesIO(csv_content.encode())
    client.post(
        f"/api/upload/transactions/{case_id}",
        files={"file": ("transactions.csv", file, "text/csv")},
    )

    # Generate narrative
    response = client.post(
        "/api/generate-narrative",
        json={"case_id": case_id},
    )

    assert response.status_code == 200
    data = response.json()
    assert "narrative" in data
    assert len(data["narrative"]) > 0
    assert "generation_mode" in data


def test_audit_trail(client):
    """Test audit trail retrieval."""
    # Create a case
    create_response = client.post("/api/cases", json={"name": "Audit Test"})
    case_id = create_response.json()["id"]

    # Get audit trail
    response = client.get(f"/api/audit/{case_id}")

    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    # Should have at least the case_created event
    assert len(data) >= 1
