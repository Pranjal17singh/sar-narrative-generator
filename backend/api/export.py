"""Export endpoints and handlers."""

from typing import Dict, Any
from datetime import datetime
from io import BytesIO
import uuid

from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from backend.processing.pdf_generator import generate_sar_pdf
from backend.models import AuditORM, AuditLogORM, AuditStatus


def generate_audit_pdf_export(audit: AuditORM, db: Session) -> StreamingResponse:
    """
    Generate PDF export for an audit.

    Returns StreamingResponse with PDF content.
    """
    # Build KYC data from customer
    customer = audit.customer
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

    # Generate PDF
    pdf_buffer = generate_sar_pdf(
        case_name=customer.name,
        case_id=str(audit.id),
        narrative=audit.final_narrative,
        kyc_data=kyc_data,
        features=audit.features or {},
        patterns=audit.patterns or [],
        created_at=audit.created_at,
    )

    # Log export
    export_log = AuditLogORM(
        id=uuid.uuid4(),
        audit_id=audit.id,
        event_type="pdf_exported",
        details={
            "narrative_length": len(audit.final_narrative or ""),
            "exported_at": datetime.utcnow().isoformat(),
        },
    )
    db.add(export_log)

    # Update audit status
    audit.status = AuditStatus.EXPORTED.value
    db.commit()

    # Return as streaming response
    filename = f"SAR_{customer.name.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d')}.pdf"

    return StreamingResponse(
        BytesIO(pdf_buffer),
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename={filename}",
        },
    )


def generate_audit_json_export(audit: AuditORM, db: Session) -> Dict[str, Any]:
    """
    Generate JSON export for an audit.

    Returns complete audit data as dictionary.
    """
    customer = audit.customer

    # Get audit logs
    logs = (
        db.query(AuditLogORM)
        .filter(AuditLogORM.audit_id == audit.id)
        .order_by(AuditLogORM.timestamp.asc())
        .all()
    )

    export_data = {
        "export_timestamp": datetime.utcnow().isoformat(),
        "export_version": "2.0",
        "audit": {
            "id": str(audit.id),
            "status": audit.status,
            "created_at": audit.created_at.isoformat() if audit.created_at else None,
            "approved_at": audit.approved_at.isoformat() if audit.approved_at else None,
        },
        "customer": {
            "id": str(customer.id),
            "name": customer.name,
            "account_number": customer.account_number,
            "account_type": customer.account_type,
            "country": customer.country,
            "occupation": customer.occupation,
            "risk_rating": customer.risk_rating,
            "pep_status": customer.pep_status,
            "sanctions_match": customer.sanctions_match,
        },
        "analysis": {
            "features": audit.features,
            "patterns": audit.patterns,
        },
        "narrative": {
            "generated": audit.generated_narrative,
            "edited": audit.edited_narrative,
            "final": audit.final_narrative,
        },
        "audit_trail": [
            {
                "id": str(log.id),
                "event_type": log.event_type,
                "timestamp": log.timestamp.isoformat(),
                "details": log.details,
            }
            for log in logs
        ],
    }

    # Log export
    export_log = AuditLogORM(
        id=uuid.uuid4(),
        audit_id=audit.id,
        event_type="json_exported",
        details={"exported_at": datetime.utcnow().isoformat()},
    )
    db.add(export_log)
    db.commit()

    return export_data
