"""Narrative generation orchestrator - LLM only."""

from typing import Dict, Any, List
import uuid

from sqlalchemy.orm import Session

from backend.llm.client import check_ollama_available, generate_completion, reset_ollama_check
from backend.llm.prompts import build_narrative_prompt, format_prompt_for_logging
from backend.models import AuditLogORM


class LLMNotAvailableError(Exception):
    """Raised when LLM is not available for narrative generation."""
    pass


def generate_sar_narrative(
    audit_id: str,
    transaction_data: List[Dict[str, Any]],
    kyc_data: Dict[str, Any],
    features: Dict[str, Any],
    patterns: List[Dict[str, Any]],
    db: Session,
) -> Dict[str, Any]:
    """
    Generate SAR narrative using LLM.

    Args:
        audit_id: Audit identifier
        transaction_data: Raw transaction records
        kyc_data: Customer KYC information
        features: Extracted features
        patterns: Detected patterns
        db: Database session for audit logging

    Returns:
        Dict with narrative, mode, patterns_included, and audit_log_id

    Raises:
        LLMNotAvailableError: If Ollama is not available
    """
    # Check if LLM is available (reset cache to get fresh status)
    reset_ollama_check()
    if not check_ollama_available():
        raise LLMNotAvailableError(
            "Ollama is not available. Please start Ollama with: ollama serve"
        )

    # Build prompt context
    prompt_data = build_narrative_prompt(kyc_data, features, patterns)

    # Get pattern types for response
    patterns_included = [p.get("pattern_type", "unknown") for p in patterns]

    # Generate with LLM
    narrative = _generate_with_llm(prompt_data)

    if narrative is None:
        raise LLMNotAvailableError(
            "LLM generation failed. Please check Ollama is running and mistral model is available."
        )

    # Log generation for audit trail
    audit_log_id = _log_narrative_generation(
        db=db,
        audit_id=audit_id,
        mode="llm",
        prompt_sent=format_prompt_for_logging(prompt_data),
        llm_response=narrative,
        retrieved_docs=prompt_data.get("context_sections", {}).get("retrieval_metadata"),
        patterns_detected=patterns,
        features_used=features,
    )

    return {
        "narrative": narrative,
        "mode": "llm",
        "patterns_included": patterns_included,
        "audit_log_id": audit_log_id,
    }


def _generate_with_llm(prompt_data: Dict[str, Any]) -> str | None:
    """
    Generate narrative using Ollama LLM.

    Returns None if generation fails.
    """
    try:
        response = generate_completion(
            prompt=prompt_data["user_prompt"],
            system_prompt=prompt_data["system_prompt"],
            temperature=0.3,
            max_tokens=800,  # Reduced for faster CPU generation
        )

        if response:
            # Clean up response
            narrative = response.strip()

            # Remove any markdown formatting that might have been added
            if narrative.startswith("```"):
                lines = narrative.split("\n")
                narrative = "\n".join(lines[1:-1] if lines[-1] == "```" else lines[1:])

            return narrative

        return None

    except Exception as e:
        print(f"LLM generation error: {e}")
        return None


def _log_narrative_generation(
    db: Session,
    audit_id: str,
    mode: str,
    prompt_sent: str,
    llm_response: str,
    retrieved_docs: Any,
    patterns_detected: List[Dict[str, Any]],
    features_used: Dict[str, Any],
) -> str:
    """Log narrative generation event to audit trail."""
    import hashlib

    # Create audit log entry
    log_id = uuid.uuid4()

    audit_log = AuditLogORM(
        id=log_id,
        audit_id=uuid.UUID(audit_id),
        event_type="narrative_generated",
        details={
            "generation_mode": mode,
            "prompt_hash": hashlib.sha256(prompt_sent.encode()).hexdigest()[:16],
            "narrative_length": len(llm_response) if llm_response else 0,
            "patterns_count": len(patterns_detected),
            "patterns": [p.get("pattern_type") for p in patterns_detected],
            "feature_summary": {
                "total_inflow": features_used.get("total_inflow", 0),
                "total_outflow": features_used.get("total_outflow", 0),
                "transaction_count": features_used.get("transaction_count", 0),
            },
        },
        prompt_sent=prompt_sent,
        llm_response=llm_response,
        retrieved_docs=retrieved_docs if isinstance(retrieved_docs, list) else None,
    )

    db.add(audit_log)
    # Don't commit here - let the caller handle the transaction

    return str(log_id)


def regenerate_narrative(
    audit_id: str,
    kyc_data: Dict[str, Any],
    features: Dict[str, Any],
    patterns: List[Dict[str, Any]],
    db: Session,
    additional_context: str = None,
) -> Dict[str, Any]:
    """
    Regenerate narrative with optional additional context.

    Useful for incorporating analyst feedback or additional information.
    """
    # If additional context provided, modify the prompt
    if additional_context:
        # Add to KYC data as analyst notes
        kyc_data = kyc_data.copy()
        kyc_data["analyst_notes"] = additional_context

    return generate_sar_narrative(
        audit_id=audit_id,
        transaction_data=[],  # Not needed for regeneration
        kyc_data=kyc_data,
        features=features,
        patterns=patterns,
        db=db,
    )
