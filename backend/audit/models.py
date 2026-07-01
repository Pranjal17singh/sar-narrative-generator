"""Audit trail data models and schemas."""

from typing import Optional, Dict, Any, List
from datetime import datetime
from enum import Enum
from pydantic import BaseModel


class AuditEventType(str, Enum):
    """Types of audit events."""
    # Case lifecycle
    CASE_CREATED = "case_created"
    CASE_DELETED = "case_deleted"
    CASE_STATUS_CHANGED = "case_status_changed"

    # Data events
    TRANSACTIONS_UPLOADED = "transactions_uploaded"
    KYC_UPLOADED = "kyc_uploaded"
    DATA_MODIFIED = "data_modified"

    # Processing events
    FEATURES_EXTRACTED = "features_extracted"
    PATTERNS_DETECTED = "patterns_detected"

    # Narrative events
    NARRATIVE_GENERATED = "narrative_generated"
    NARRATIVE_EDITED = "narrative_edited"
    NARRATIVE_APPROVED = "narrative_approved"

    # Export events
    PDF_EXPORTED = "pdf_exported"
    CASE_EXPORTED = "case_exported"

    # LLM events
    LLM_PROMPT_SENT = "llm_prompt_sent"
    LLM_RESPONSE_RECEIVED = "llm_response_received"
    RAG_RETRIEVAL = "rag_retrieval"


class AuditEntry(BaseModel):
    """Audit log entry schema."""
    id: str
    case_id: str
    event_type: AuditEventType
    timestamp: datetime
    data_hash: Optional[str] = None
    details: Dict[str, Any] = {}
    user_action: Optional[str] = None

    # LLM-specific fields
    prompt_sent: Optional[str] = None
    llm_response: Optional[str] = None
    retrieved_docs: Optional[List[Dict[str, Any]]] = None

    class Config:
        use_enum_values = True


class AuditSummary(BaseModel):
    """Summary of audit trail for a case."""
    case_id: str
    total_events: int
    first_event: Optional[datetime] = None
    last_event: Optional[datetime] = None
    event_types: List[str]
    data_modifications: int
    narrative_edits: int
    llm_calls: int


class ComplianceReport(BaseModel):
    """Compliance report for regulatory purposes."""
    case_id: str
    case_name: str
    generated_at: datetime
    review_period_start: Optional[str] = None
    review_period_end: Optional[str] = None

    # Data integrity
    input_data_hash: str
    transaction_count: int

    # Processing chain
    features_extracted: bool
    patterns_detected: List[str]
    pattern_confidence_scores: Dict[str, float]

    # Narrative generation
    generation_mode: str  # "llm" or "template"
    prompt_used: bool
    retrieved_context_count: int

    # Human review
    narrative_edited: bool
    edit_count: int
    approved_by: Optional[str] = None
    approved_at: Optional[datetime] = None

    # Export
    exported: bool
    export_format: Optional[str] = None
    export_timestamp: Optional[datetime] = None
