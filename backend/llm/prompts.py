"""Prompt template assembly for SAR narrative generation."""

from typing import Dict, Any, List

from backend.rag.retriever import build_rag_prompt_context


SYSTEM_PROMPT = """You are a compliance analyst writing SAR narratives. Be factual, specific with amounts and dates, and use professional language. Do not speculate about criminal intent."""


NARRATIVE_PROMPT_TEMPLATE = """Write a SAR narrative for this case:

CUSTOMER: {customer_info}

TRANSACTIONS: {transaction_summary}

PATTERNS: {patterns_detected}

Write a 300-400 word narrative covering: subject identification, suspicious activity details, amounts and dates, and recommended actions."""


def build_narrative_prompt(
    kyc_data: Dict[str, Any],
    features: Dict[str, Any],
    patterns: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Build complete prompt for narrative generation.

    Returns dict with:
        - system_prompt: System instructions
        - user_prompt: Full prompt with context
        - context_sections: Individual sections for audit
    """
    # Get RAG context
    context_sections = build_rag_prompt_context(kyc_data, features, patterns)

    # Build user prompt (simplified to reduce processing time on CPU)
    user_prompt = NARRATIVE_PROMPT_TEMPLATE.format(
        customer_info=context_sections["customer_info"],
        transaction_summary=context_sections["transaction_summary"],
        patterns_detected=context_sections["patterns_detected"],
    )

    return {
        "system_prompt": SYSTEM_PROMPT,
        "user_prompt": user_prompt,
        "context_sections": context_sections,
    }


def build_chat_messages(
    kyc_data: Dict[str, Any],
    features: Dict[str, Any],
    patterns: List[Dict[str, Any]],
) -> List[Dict[str, str]]:
    """
    Build chat-format messages for Ollama chat API.
    """
    prompt_data = build_narrative_prompt(kyc_data, features, patterns)

    return [
        {"role": "system", "content": prompt_data["system_prompt"]},
        {"role": "user", "content": prompt_data["user_prompt"]},
    ]


def format_prompt_for_logging(prompt_data: Dict[str, Any]) -> str:
    """Format prompt data for audit logging."""
    return f"""=== SYSTEM PROMPT ===
{prompt_data['system_prompt']}

=== USER PROMPT ===
{prompt_data['user_prompt']}"""
