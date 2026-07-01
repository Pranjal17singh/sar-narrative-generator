"""Audit event capture and logging."""

from typing import Dict, Any, List, Optional
from datetime import datetime
import hashlib
import json
import uuid

from sqlalchemy.orm import Session

from backend.models import AuditLogORM
from backend.audit.models import AuditEventType


def log_event(
    db: Session,
    case_id: str,
    event_type: str,
    details: Dict[str, Any] = None,
    user_action: str = None,
    data_hash: str = None,
) -> str:
    """
    Log a generic audit event.

    Returns the audit log ID.
    """
    audit_log = AuditLogORM(
        id=str(uuid.uuid4()),
        case_id=case_id,
        event_type=event_type,
        timestamp=datetime.utcnow(),
        details=details or {},
        user_action=user_action,
        data_hash=data_hash,
    )

    db.add(audit_log)
    db.commit()

    return audit_log.id


def log_narrative_generation(
    db: Session,
    case_id: str,
    mode: str,
    prompt_sent: str,
    llm_response: str,
    retrieved_docs: Dict[str, Any] = None,
    patterns_detected: List[Dict[str, Any]] = None,
    features_used: Dict[str, Any] = None,
) -> str:
    """
    Log narrative generation with full prompt/response capture.

    This is critical for audit compliance - captures the complete
    chain of inputs and outputs.
    """
    # Create hash of the prompt for integrity verification
    prompt_hash = hashlib.sha256(prompt_sent.encode()).hexdigest()

    details = {
        "generation_mode": mode,
        "prompt_hash": prompt_hash,
        "response_length": len(llm_response),
        "patterns_count": len(patterns_detected) if patterns_detected else 0,
        "patterns": [p.get("pattern_type") for p in (patterns_detected or [])],
    }

    if features_used:
        details["features_summary"] = {
            "transaction_count": features_used.get("transaction_count"),
            "total_inflow": features_used.get("total_inflow"),
            "total_outflow": features_used.get("total_outflow"),
        }

    audit_log = AuditLogORM(
        id=str(uuid.uuid4()),
        case_id=case_id,
        event_type=AuditEventType.NARRATIVE_GENERATED.value,
        timestamp=datetime.utcnow(),
        details=details,
        prompt_sent=prompt_sent,
        llm_response=llm_response,
        retrieved_docs=retrieved_docs,
    )

    db.add(audit_log)
    db.commit()

    return audit_log.id


def log_data_upload(
    db: Session,
    case_id: str,
    upload_type: str,  # "transactions" or "kyc"
    filename: str,
    record_count: int,
    data: Any,
) -> str:
    """
    Log data upload with integrity hash.
    """
    # Create hash of uploaded data
    data_json = json.dumps(data, sort_keys=True, default=str)
    data_hash = hashlib.sha256(data_json.encode()).hexdigest()

    event_type = (
        AuditEventType.TRANSACTIONS_UPLOADED.value
        if upload_type == "transactions"
        else AuditEventType.KYC_UPLOADED.value
    )

    return log_event(
        db=db,
        case_id=case_id,
        event_type=event_type,
        details={
            "filename": filename,
            "record_count": record_count,
            "data_hash": data_hash,
        },
        data_hash=data_hash,
    )


def log_feature_extraction(
    db: Session,
    case_id: str,
    features: Dict[str, Any],
) -> str:
    """Log feature extraction results."""
    return log_event(
        db=db,
        case_id=case_id,
        event_type=AuditEventType.FEATURES_EXTRACTED.value,
        details={
            "feature_count": len(features),
            "key_features": {
                "transaction_count": features.get("transaction_count"),
                "total_inflow": features.get("total_inflow"),
                "total_outflow": features.get("total_outflow"),
                "unique_counterparties": features.get("unique_counterparties"),
            },
        },
    )


def log_pattern_detection(
    db: Session,
    case_id: str,
    patterns: List[Dict[str, Any]],
) -> str:
    """Log pattern detection results."""
    pattern_summary = [
        {
            "type": p.get("pattern_type"),
            "confidence": p.get("confidence"),
            "severity": p.get("severity"),
        }
        for p in patterns
    ]

    return log_event(
        db=db,
        case_id=case_id,
        event_type=AuditEventType.PATTERNS_DETECTED.value,
        details={
            "patterns_detected": len(patterns),
            "pattern_summary": pattern_summary,
        },
    )


def log_narrative_edit(
    db: Session,
    case_id: str,
    original_narrative: str,
    edited_narrative: str,
    editor_notes: str = None,
) -> str:
    """Log narrative edit with change tracking."""
    # Calculate simple diff metrics
    original_len = len(original_narrative) if original_narrative else 0
    edited_len = len(edited_narrative)
    change_ratio = abs(edited_len - original_len) / max(original_len, 1)

    return log_event(
        db=db,
        case_id=case_id,
        event_type=AuditEventType.NARRATIVE_EDITED.value,
        details={
            "original_length": original_len,
            "edited_length": edited_len,
            "change_ratio": round(change_ratio, 3),
            "editor_notes": editor_notes,
        },
        user_action="manual_edit",
    )


def log_narrative_approval(
    db: Session,
    case_id: str,
    approver_notes: str = None,
    narrative_hash: str = None,
) -> str:
    """Log narrative approval."""
    return log_event(
        db=db,
        case_id=case_id,
        event_type=AuditEventType.NARRATIVE_APPROVED.value,
        details={
            "approver_notes": approver_notes,
            "narrative_hash": narrative_hash,
        },
        user_action="approval",
    )


def log_export(
    db: Session,
    case_id: str,
    export_format: str,
    export_details: Dict[str, Any] = None,
) -> str:
    """Log case export."""
    return log_event(
        db=db,
        case_id=case_id,
        event_type=AuditEventType.PDF_EXPORTED.value,
        details={
            "export_format": export_format,
            **(export_details or {}),
        },
        user_action="export",
    )


def get_audit_trail(db: Session, case_id: str) -> List[Dict[str, Any]]:
    """
    Get complete audit trail for a case.
    """
    logs = (
        db.query(AuditLogORM)
        .filter(AuditLogORM.case_id == case_id)
        .order_by(AuditLogORM.timestamp.asc())
        .all()
    )

    return [
        {
            "id": log.id,
            "event_type": log.event_type,
            "timestamp": log.timestamp.isoformat(),
            "details": log.details,
            "user_action": log.user_action,
            "has_prompt": bool(log.prompt_sent),
            "has_response": bool(log.llm_response),
        }
        for log in logs
    ]


def get_compliance_summary(db: Session, case_id: str) -> Dict[str, Any]:
    """
    Generate compliance summary for a case.
    """
    logs = (
        db.query(AuditLogORM)
        .filter(AuditLogORM.case_id == case_id)
        .order_by(AuditLogORM.timestamp.asc())
        .all()
    )

    if not logs:
        return {"case_id": case_id, "events": 0}

    event_types = [log.event_type for log in logs]

    return {
        "case_id": case_id,
        "total_events": len(logs),
        "first_event": logs[0].timestamp.isoformat(),
        "last_event": logs[-1].timestamp.isoformat(),
        "event_types": list(set(event_types)),
        "data_uploads": event_types.count(AuditEventType.TRANSACTIONS_UPLOADED.value)
                       + event_types.count(AuditEventType.KYC_UPLOADED.value),
        "narrative_generations": event_types.count(AuditEventType.NARRATIVE_GENERATED.value),
        "narrative_edits": event_types.count(AuditEventType.NARRATIVE_EDITED.value),
        "approved": AuditEventType.NARRATIVE_APPROVED.value in event_types,
        "exported": AuditEventType.PDF_EXPORTED.value in event_types,
    }
