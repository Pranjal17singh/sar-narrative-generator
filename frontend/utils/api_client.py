"""Backend API client for Streamlit frontend."""

from typing import Dict, Any, List, Optional
import requests

# API base URL
API_BASE = "http://localhost:8000/api"


class APIClient:
    """Client for interacting with the SAR backend API."""

    def __init__(self, base_url: str = API_BASE):
        self.base_url = base_url

    def _request(
        self,
        method: str,
        endpoint: str,
        data: Dict = None,
        files: Dict = None,
        params: Dict = None,
    ) -> Dict[str, Any]:
        """Make HTTP request to API."""
        url = f"{self.base_url}{endpoint}"

        try:
            if method == "GET":
                response = requests.get(url, params=params, timeout=30)
            elif method == "POST":
                if files:
                    response = requests.post(url, files=files, data=data, timeout=60)
                else:
                    response = requests.post(url, json=data, timeout=120)
            elif method == "DELETE":
                response = requests.delete(url, timeout=30)
            else:
                raise ValueError(f"Unsupported method: {method}")

            if response.status_code >= 400:
                error_detail = response.json().get("detail", response.text)
                return {"error": True, "message": error_detail, "status": response.status_code}

            return response.json()

        except requests.exceptions.ConnectionError:
            return {"error": True, "message": "Cannot connect to backend. Is the server running?"}
        except requests.exceptions.Timeout:
            return {"error": True, "message": "Request timed out"}
        except Exception as e:
            return {"error": True, "message": str(e)}

    # Health check
    def health_check(self) -> Dict[str, Any]:
        """Check backend health and Ollama status."""
        try:
            response = requests.get(f"{self.base_url.replace('/api', '')}/health", timeout=5)
            return response.json()
        except:
            return {"status": "unavailable", "ollama_available": False}

    # ============= Customer Endpoints =============

    def list_customers(self, risk_rating: str = None) -> List[Dict[str, Any]]:
        """List all customers with optional risk filter."""
        params = {"risk_rating": risk_rating} if risk_rating else None
        result = self._request("GET", "/customers", params=params)
        if isinstance(result, dict) and result.get("error"):
            return []
        return result if isinstance(result, list) else []

    def get_customer(self, customer_id: str) -> Dict[str, Any]:
        """Get customer profile with transactions."""
        return self._request("GET", f"/customers/{customer_id}")

    # ============= Audit Endpoints =============

    def start_audit(self, customer_id: str) -> Dict[str, Any]:
        """Start an audit for a customer."""
        return self._request("POST", f"/customers/{customer_id}/audit")

    def list_audits(self, status: str = None) -> List[Dict[str, Any]]:
        """List all audits with optional status filter."""
        params = {"status": status} if status else None
        result = self._request("GET", "/audits", params=params)
        if isinstance(result, dict) and result.get("error"):
            return []
        return result if isinstance(result, list) else []

    def get_audit(self, audit_id: str) -> Dict[str, Any]:
        """Get audit details including features, patterns, and narrative."""
        return self._request("GET", f"/audits/{audit_id}")

    def edit_narrative(self, audit_id: str, narrative: str) -> Dict[str, Any]:
        """Save edited narrative."""
        return self._request("POST", f"/audits/{audit_id}/edit", data={
            "edited_narrative": narrative,
        })

    def approve_narrative(self, audit_id: str, notes: str = None) -> Dict[str, Any]:
        """Approve narrative."""
        data = {"approver_notes": notes} if notes else {}
        return self._request("POST", f"/audits/{audit_id}/approve", data=data)

    def get_audit_logs(self, audit_id: str) -> List[Dict[str, Any]]:
        """Get audit trail for an audit."""
        result = self._request("GET", f"/audits/{audit_id}/logs")
        if isinstance(result, dict) and result.get("error"):
            return []
        return result if isinstance(result, list) else []

    def export_pdf(self, audit_id: str) -> bytes:
        """Export audit as PDF."""
        url = f"{self.base_url}/audits/{audit_id}/export/pdf"
        try:
            response = requests.get(url, timeout=30)
            if response.status_code == 200:
                return response.content
            return None
        except:
            return None


# Singleton client instance
_client = None


def get_client() -> APIClient:
    """Get API client instance."""
    global _client
    if _client is None:
        _client = APIClient()
    return _client
