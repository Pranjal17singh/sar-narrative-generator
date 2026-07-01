"""Pydantic and SQLAlchemy models for SAR Narrative Generator."""

from datetime import datetime
from typing import Optional, List, Dict, Any
from enum import Enum
from decimal import Decimal
import uuid

from pydantic import BaseModel, Field
from sqlalchemy import Column, String, Boolean, DateTime, Text, Numeric, ForeignKey, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship

from backend.database import Base


# ============= Enums =============

class RiskRating(str, Enum):
    """Customer risk rating levels."""
    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"


class AuditStatus(str, Enum):
    """Status of an audit."""
    PROCESSING = "processing"
    REVIEW = "review"
    APPROVED = "approved"
    EXPORTED = "exported"


class PatternType(str, Enum):
    """Types of suspicious patterns."""
    FUNNEL = "funnel"
    RAPID_MOVEMENT = "rapid_movement"
    STRUCTURING = "structuring"
    CROSS_BORDER = "cross_border"
    ROUND_AMOUNTS = "round_amounts"
    VELOCITY_SPIKE = "velocity_spike"


# ============= SQLAlchemy ORM Models =============

class CustomerORM(Base):
    """Database model for customers (pre-loaded)."""
    __tablename__ = "customers"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False)
    account_number = Column(String, unique=True, nullable=False)
    account_type = Column(String, nullable=True)
    country = Column(String, default="US")
    occupation = Column(String, nullable=True)
    risk_rating = Column(String, default="Low")  # Low, Medium, High
    pep_status = Column(Boolean, default=False)
    sanctions_match = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    transactions = relationship("TransactionORM", back_populates="customer", cascade="all, delete-orphan")
    audits = relationship("AuditORM", back_populates="customer", cascade="all, delete-orphan")


class TransactionORM(Base):
    """Database model for transactions (pre-loaded)."""
    __tablename__ = "transactions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    customer_id = Column(UUID(as_uuid=True), ForeignKey("customers.id"), nullable=False)
    date = Column(DateTime, nullable=False)
    amount = Column(Numeric(15, 2), nullable=False)
    currency = Column(String, default="USD")
    transaction_type = Column(String, nullable=False)  # credit/debit
    counterparty = Column(String, nullable=True)
    counterparty_country = Column(String, nullable=True)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    customer = relationship("CustomerORM", back_populates="transactions")


class AuditORM(Base):
    """Database model for audits (created on 'Start Audit')."""
    __tablename__ = "audits"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    customer_id = Column(UUID(as_uuid=True), ForeignKey("customers.id"), nullable=False)
    status = Column(String, default=AuditStatus.PROCESSING.value)
    features = Column(JSONB, default=dict)
    patterns = Column(JSONB, default=list)
    generated_narrative = Column(Text, nullable=True)
    edited_narrative = Column(Text, nullable=True)
    final_narrative = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    approved_at = Column(DateTime, nullable=True)

    # Relationships
    customer = relationship("CustomerORM", back_populates="audits")
    audit_logs = relationship("AuditLogORM", back_populates="audit", cascade="all, delete-orphan")


class AuditLogORM(Base):
    """Database model for audit trail (full traceability)."""
    __tablename__ = "audit_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    audit_id = Column(UUID(as_uuid=True), ForeignKey("audits.id"), nullable=False)
    event_type = Column(String, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)
    details = Column(JSONB, default=dict)
    prompt_sent = Column(Text, nullable=True)
    llm_response = Column(Text, nullable=True)
    retrieved_docs = Column(JSONB, nullable=True)

    # Relationships
    audit = relationship("AuditORM", back_populates="audit_logs")


# ============= Pydantic Models =============

class CustomerBase(BaseModel):
    """Base customer model."""
    name: str
    account_number: str
    account_type: Optional[str] = None
    country: str = "US"
    occupation: Optional[str] = None
    risk_rating: str = "Low"
    pep_status: bool = False
    sanctions_match: bool = False


class CustomerResponse(BaseModel):
    """Response model for customer data."""
    id: str
    name: str
    account_number: str
    account_type: Optional[str] = None
    country: str = "US"
    occupation: Optional[str] = None
    risk_rating: str = "Low"
    pep_status: bool = False
    sanctions_match: bool = False
    created_at: datetime
    transaction_count: int = 0

    class Config:
        from_attributes = True


class CustomerDetailResponse(BaseModel):
    """Detailed customer response with transactions."""
    id: str
    name: str
    account_number: str
    account_type: Optional[str] = None
    country: str = "US"
    occupation: Optional[str] = None
    risk_rating: str = "Low"
    pep_status: bool = False
    sanctions_match: bool = False
    created_at: datetime
    transactions: List[Dict[str, Any]] = []

    class Config:
        from_attributes = True


class TransactionResponse(BaseModel):
    """Response model for transaction data."""
    id: str
    customer_id: str
    date: datetime
    amount: float
    currency: str = "USD"
    transaction_type: str
    counterparty: Optional[str] = None
    counterparty_country: Optional[str] = None
    description: Optional[str] = None

    class Config:
        from_attributes = True


class ExtractedFeatures(BaseModel):
    """Features extracted from transaction data."""
    total_inflow: float = 0.0
    total_outflow: float = 0.0
    net_flow: float = 0.0
    transaction_count: int = 0
    unique_counterparties: int = 0
    cross_border_count: int = 0
    cross_border_percentage: float = 0.0
    avg_transaction_amount: float = 0.0
    max_transaction_amount: float = 0.0
    min_transaction_amount: float = 0.0
    weekend_transaction_count: int = 0
    off_hours_transaction_count: int = 0
    round_amount_count: int = 0
    transactions_per_day: float = 0.0
    date_range_days: int = 0
    currency_count: int = 1


class PatternMatch(BaseModel):
    """Detected suspicious pattern."""
    pattern_type: PatternType
    confidence: float = Field(ge=0.0, le=1.0)
    description: str
    evidence: List[Dict[str, Any]] = []
    severity: str = "medium"  # low, medium, high


class AuditResponse(BaseModel):
    """Response model for audit data."""
    id: str
    customer_id: str
    customer_name: str
    status: str
    features: Dict[str, Any] = {}
    patterns: List[Dict[str, Any]] = []
    generated_narrative: Optional[str] = None
    edited_narrative: Optional[str] = None
    final_narrative: Optional[str] = None
    created_at: datetime
    approved_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class AuditListResponse(BaseModel):
    """List response for audits."""
    id: str
    customer_id: str
    customer_name: str
    status: str
    created_at: datetime
    approved_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class NarrativeEditRequest(BaseModel):
    """Request to edit narrative."""
    edited_narrative: str


class NarrativeApproveRequest(BaseModel):
    """Request to approve narrative."""
    approver_notes: Optional[str] = None


class AuditLogResponse(BaseModel):
    """Response model for audit log."""
    id: str
    audit_id: str
    event_type: str
    timestamp: datetime
    details: Dict[str, Any] = {}
    prompt_sent: Optional[str] = None
    llm_response: Optional[str] = None
    retrieved_docs: Optional[List[Dict[str, Any]]] = None

    class Config:
        from_attributes = True


class StartAuditResponse(BaseModel):
    """Response for starting an audit."""
    audit_id: str
    customer_id: str
    status: str
    message: str
