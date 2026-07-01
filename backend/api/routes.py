"""API route definitions for customer-centric SAR workflow."""

from typing import List, Optional
from datetime import datetime
import hashlib
import json
import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import (
    CustomerORM,
    TransactionORM,
    AuditORM,
    AuditLogORM,
    AuditStatus,
    CustomerResponse,
    CustomerDetailResponse,
    AuditResponse,
    AuditListResponse,
    AuditLogResponse,
    NarrativeEditRequest,
    NarrativeApproveRequest,
    StartAuditResponse,
)
from backend.processing.features import extract_features
from backend.patterns.detector import detect_patterns

router = APIRouter()


# ============= Customer Endpoints =============

@router.get("/customers", response_model=List[CustomerResponse])
def list_customers(
    risk_rating: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
):
    """List all customers with optional risk filter."""
    query = db.query(CustomerORM)

    if risk_rating:
        query = query.filter(CustomerORM.risk_rating == risk_rating)

    customers = query.order_by(CustomerORM.created_at.desc()).offset(skip).limit(limit).all()

    return [
        CustomerResponse(
            id=str(c.id),
            name=c.name,
            account_number=c.account_number,
            account_type=c.account_type,
            country=c.country,
            occupation=c.occupation,
            risk_rating=c.risk_rating,
            pep_status=c.pep_status,
            sanctions_match=c.sanctions_match,
            created_at=c.created_at,
            transaction_count=len(c.transactions) if c.transactions else 0,
        )
        for c in customers
    ]


@router.get("/customers/{customer_id}", response_model=CustomerDetailResponse)
def get_customer(customer_id: str, db: Session = Depends(get_db)):
    """Get customer profile with transactions."""
    try:
        cust_uuid = uuid.UUID(customer_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid customer ID format")

    customer = db.query(CustomerORM).filter(CustomerORM.id == cust_uuid).first()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")

    # Get transactions sorted by date
    transactions = (
        db.query(TransactionORM)
        .filter(TransactionORM.customer_id == cust_uuid)
        .order_by(TransactionORM.date.desc())
        .all()
    )

    return CustomerDetailResponse(
        id=str(customer.id),
        name=customer.name,
        account_number=customer.account_number,
        account_type=customer.account_type,
        country=customer.country,
        occupation=customer.occupation,
        risk_rating=customer.risk_rating,
        pep_status=customer.pep_status,
        sanctions_match=customer.sanctions_match,
        created_at=customer.created_at,
        transactions=[
            {
                "id": str(t.id),
                "date": t.date.isoformat(),
                "amount": float(t.amount),
                "currency": t.currency,
                "transaction_type": t.transaction_type,
                "counterparty": t.counterparty,
                "counterparty_country": t.counterparty_country,
                "description": t.description,
            }
            for t in transactions
        ],
    )


# ============= Audit Endpoints =============

@router.post("/customers/{customer_id}/audit", response_model=StartAuditResponse)
def start_audit(customer_id: str, db: Session = Depends(get_db)):
    """Start an audit for a customer - triggers analysis and narrative generation."""
    try:
        cust_uuid = uuid.UUID(customer_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid customer ID format")

    customer = db.query(CustomerORM).filter(CustomerORM.id == cust_uuid).first()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")

    # Get customer transactions
    transactions = (
        db.query(TransactionORM)
        .filter(TransactionORM.customer_id == cust_uuid)
        .order_by(TransactionORM.date.asc())
        .all()
    )

    if not transactions:
        raise HTTPException(status_code=400, detail="Customer has no transactions")

    # Convert transactions to dict format for processing
    txn_data = [
        {
            "transaction_id": str(t.id),
            "date": t.date.isoformat(),
            "amount": float(t.amount),
            "currency": t.currency,
            "transaction_type": t.transaction_type,
            "counterparty": t.counterparty,
            "country": t.counterparty_country,
            "description": t.description,
        }
        for t in transactions
    ]

    # Create audit record
    audit = AuditORM(
        id=uuid.uuid4(),
        customer_id=cust_uuid,
        status=AuditStatus.PROCESSING.value,
    )
    db.add(audit)
    db.flush()

    # Log audit start
    audit_log = AuditLogORM(
        id=uuid.uuid4(),
        audit_id=audit.id,
        event_type="audit_started",
        details={
            "customer_name": customer.name,
            "transaction_count": len(txn_data),
        },
    )
    db.add(audit_log)

    # Extract features
    features = extract_features(txn_data)
    audit.features = features

    # Log feature extraction
    feature_log = AuditLogORM(
        id=uuid.uuid4(),
        audit_id=audit.id,
        event_type="features_extracted",
        details={
            "feature_count": len(features),
            "total_inflow": features.get("total_inflow", 0),
            "total_outflow": features.get("total_outflow", 0),
        },
    )
    db.add(feature_log)

    # Detect patterns
    patterns = detect_patterns(txn_data, features)
    audit.patterns = [p.model_dump() for p in patterns]

    # Log pattern detection
    pattern_log = AuditLogORM(
        id=uuid.uuid4(),
        audit_id=audit.id,
        event_type="patterns_detected",
        details={
            "pattern_count": len(patterns),
            "patterns": [p.pattern_type for p in patterns],
        },
    )
    db.add(pattern_log)

    # Build KYC data from customer
    kyc_data = {
        "customer_id": str(customer.id),
        "name": customer.name,
        "account_number": customer.account_number,
        "account_type": customer.account_type,
        "country": customer.country,
        "occupation": customer.occupation,
        "risk_rating": customer.risk_rating,
        "pep_status": customer.pep_status,
        "sanctions_match": customer.sanctions_match,
    }

    # Generate narrative
    from backend.llm.generator import generate_sar_narrative, LLMNotAvailableError

    try:
        result = generate_sar_narrative(
            audit_id=str(audit.id),
            transaction_data=txn_data,
            kyc_data=kyc_data,
            features=features,
            patterns=audit.patterns,
            db=db,
        )

        audit.generated_narrative = result["narrative"]
        audit.status = AuditStatus.REVIEW.value

        db.commit()

        return StartAuditResponse(
            audit_id=str(audit.id),
            customer_id=customer_id,
            status=audit.status,
            message=f"Audit started. Detected {len(patterns)} patterns.",
        )

    except LLMNotAvailableError as e:
        db.rollback()
        raise HTTPException(
            status_code=503,
            detail=str(e)
        )


@router.get("/audits", response_model=List[AuditListResponse])
def list_audits(
    status: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
):
    """List all audits with optional status filter."""
    query = db.query(AuditORM).join(CustomerORM)

    if status:
        query = query.filter(AuditORM.status == status)

    audits = query.order_by(AuditORM.created_at.desc()).offset(skip).limit(limit).all()

    return [
        AuditListResponse(
            id=str(a.id),
            customer_id=str(a.customer_id),
            customer_name=a.customer.name,
            status=a.status,
            created_at=a.created_at,
            approved_at=a.approved_at,
        )
        for a in audits
    ]


@router.get("/audits/{audit_id}", response_model=AuditResponse)
def get_audit(audit_id: str, db: Session = Depends(get_db)):
    """Get audit details including features, patterns, and narrative."""
    try:
        audit_uuid = uuid.UUID(audit_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid audit ID format")

    audit = db.query(AuditORM).filter(AuditORM.id == audit_uuid).first()
    if not audit:
        raise HTTPException(status_code=404, detail="Audit not found")

    return AuditResponse(
        id=str(audit.id),
        customer_id=str(audit.customer_id),
        customer_name=audit.customer.name,
        status=audit.status,
        features=audit.features or {},
        patterns=audit.patterns or [],
        generated_narrative=audit.generated_narrative,
        edited_narrative=audit.edited_narrative,
        final_narrative=audit.final_narrative,
        created_at=audit.created_at,
        approved_at=audit.approved_at,
    )


@router.post("/audits/{audit_id}/edit")
def edit_narrative(
    audit_id: str,
    request: NarrativeEditRequest,
    db: Session = Depends(get_db),
):
    """Save edited narrative."""
    try:
        audit_uuid = uuid.UUID(audit_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid audit ID format")

    audit = db.query(AuditORM).filter(AuditORM.id == audit_uuid).first()
    if not audit:
        raise HTTPException(status_code=404, detail="Audit not found")

    audit.edited_narrative = request.edited_narrative

    # Log edit
    edit_log = AuditLogORM(
        id=uuid.uuid4(),
        audit_id=audit.id,
        event_type="narrative_edited",
        details={
            "original_length": len(audit.generated_narrative or ""),
            "edited_length": len(request.edited_narrative),
        },
    )
    db.add(edit_log)
    db.commit()

    return {"message": "Narrative saved", "audit_id": audit_id}


@router.post("/audits/{audit_id}/approve")
def approve_narrative(
    audit_id: str,
    request: NarrativeApproveRequest = None,
    db: Session = Depends(get_db),
):
    """Approve and finalize narrative."""
    try:
        audit_uuid = uuid.UUID(audit_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid audit ID format")

    audit = db.query(AuditORM).filter(AuditORM.id == audit_uuid).first()
    if not audit:
        raise HTTPException(status_code=404, detail="Audit not found")

    # Use edited narrative if available, otherwise generated
    final_narrative = audit.edited_narrative or audit.generated_narrative
    if not final_narrative:
        raise HTTPException(status_code=400, detail="No narrative to approve")

    audit.final_narrative = final_narrative
    audit.status = AuditStatus.APPROVED.value
    audit.approved_at = datetime.utcnow()

    # Log approval
    approval_log = AuditLogORM(
        id=uuid.uuid4(),
        audit_id=audit.id,
        event_type="narrative_approved",
        details={
            "approver_notes": request.approver_notes if request else None,
            "narrative_length": len(final_narrative),
        },
    )
    db.add(approval_log)
    db.commit()

    return {"message": "Narrative approved", "audit_id": audit_id}


@router.get("/audits/{audit_id}/export/pdf")
def export_audit_pdf(audit_id: str, db: Session = Depends(get_db)):
    """Export audit as PDF."""
    from backend.api.export import generate_audit_pdf_export

    try:
        audit_uuid = uuid.UUID(audit_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid audit ID format")

    audit = db.query(AuditORM).filter(AuditORM.id == audit_uuid).first()
    if not audit:
        raise HTTPException(status_code=404, detail="Audit not found")

    if not audit.final_narrative:
        raise HTTPException(status_code=400, detail="Narrative must be approved before export")

    return generate_audit_pdf_export(audit, db)


@router.get("/audits/{audit_id}/logs", response_model=List[AuditLogResponse])
def get_audit_logs(audit_id: str, db: Session = Depends(get_db)):
    """Get audit trail for an audit."""
    try:
        audit_uuid = uuid.UUID(audit_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid audit ID format")

    audit = db.query(AuditORM).filter(AuditORM.id == audit_uuid).first()
    if not audit:
        raise HTTPException(status_code=404, detail="Audit not found")

    logs = (
        db.query(AuditLogORM)
        .filter(AuditLogORM.audit_id == audit_uuid)
        .order_by(AuditLogORM.timestamp.asc())
        .all()
    )

    return [
        AuditLogResponse(
            id=str(log.id),
            audit_id=str(log.audit_id),
            event_type=log.event_type,
            timestamp=log.timestamp,
            details=log.details or {},
            prompt_sent=log.prompt_sent,
            llm_response=log.llm_response,
            retrieved_docs=log.retrieved_docs,
        )
        for log in logs
    ]
