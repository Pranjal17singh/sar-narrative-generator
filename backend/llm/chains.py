"""LangChain chains for SAR narrative generation."""

from typing import Dict, Any, List, Optional
from functools import lru_cache

from langchain.prompts import ChatPromptTemplate, SystemMessagePromptTemplate, HumanMessagePromptTemplate
from langchain.chains import LLMChain
from langchain_community.llms import Ollama
from langchain.callbacks.manager import CallbackManager

from backend.config import get_settings
from backend.llm.langchain_callbacks import AuditCallbackHandler


settings = get_settings()


# System prompt for SAR narrative generation
SAR_SYSTEM_PROMPT = """You are an expert Bank Secrecy Act (BSA) compliance analyst specializing in writing Suspicious Activity Report (SAR) narratives. Your task is to generate clear, compliant, and comprehensive SAR narratives following FinCEN guidelines.

Key requirements:
1. Use professional, objective language
2. Include specific transaction details with dates, amounts, and parties
3. Describe the suspicious activity patterns detected
4. Reference the customer's risk indicators (PEP status, sanctions, risk rating)
5. Follow the "5 W's" structure: Who, What, When, Where, Why suspicious
6. Avoid speculation - stick to observable facts and patterns
7. Include relevant BSA/AML typology references when applicable

The narrative should be suitable for regulatory filing and internal compliance review."""


SAR_USER_PROMPT_TEMPLATE = """Generate a SAR narrative for the following case:

## Customer Information
- Name: {customer_name}
- Account Number: {account_number}
- Account Type: {account_type}
- Country: {country}
- Occupation: {occupation}
- Risk Rating: {risk_rating}
- PEP Status: {pep_status}
- Sanctions Match: {sanctions_match}

## Transaction Summary
- Total Transactions: {transaction_count}
- Date Range: {date_range}
- Total Inflow: ${total_inflow:,.2f}
- Total Outflow: ${total_outflow:,.2f}
- Net Flow: ${net_flow:,.2f}
- Cross-Border Transactions: {cross_border_count} ({cross_border_percentage:.1f}%)
- Unique Counterparties: {unique_counterparties}

## Detected Suspicious Patterns
{patterns_section}

## Additional Context
{additional_context}

Please generate a comprehensive SAR narrative that:
1. Opens with the subject and account identification
2. Describes the suspicious activity observed
3. Details the specific patterns detected with supporting evidence
4. Explains why this activity is suspicious
5. Concludes with the reason for filing

Generate the narrative now:"""


def get_sar_prompt_template() -> ChatPromptTemplate:
    """Create the SAR narrative generation prompt template."""
    system_message = SystemMessagePromptTemplate.from_template(SAR_SYSTEM_PROMPT)
    human_message = HumanMessagePromptTemplate.from_template(SAR_USER_PROMPT_TEMPLATE)

    return ChatPromptTemplate.from_messages([system_message, human_message])


@lru_cache(maxsize=1)
def get_ollama_llm(temperature: float = 0.3) -> Optional[Ollama]:
    """Get cached Ollama LLM instance."""
    try:
        llm = Ollama(
            base_url=settings.ollama_base_url,
            model=settings.ollama_model,
            temperature=temperature,
            num_predict=2000,
            timeout=settings.ollama_timeout,
        )
        return llm
    except Exception as e:
        print(f"Failed to initialize Ollama: {e}")
        return None


def create_sar_chain(
    audit_callback: Optional[AuditCallbackHandler] = None
) -> Optional[LLMChain]:
    """
    Create a LangChain chain for SAR narrative generation.

    Args:
        audit_callback: Optional callback handler for audit logging

    Returns:
        LLMChain instance or None if LLM unavailable
    """
    llm = get_ollama_llm()
    if llm is None:
        return None

    prompt = get_sar_prompt_template()

    # Set up callbacks if provided
    callback_manager = None
    if audit_callback:
        callback_manager = CallbackManager([audit_callback])

    chain = LLMChain(
        llm=llm,
        prompt=prompt,
        callback_manager=callback_manager,
        verbose=settings.debug,
    )

    return chain


def format_patterns_for_prompt(patterns: List[Dict[str, Any]]) -> str:
    """Format detected patterns for inclusion in the prompt."""
    if not patterns:
        return "No specific suspicious patterns detected."

    sections = []
    for i, pattern in enumerate(patterns, 1):
        pattern_type = pattern.get("pattern_type", "unknown").replace("_", " ").title()
        confidence = pattern.get("confidence", 0) * 100
        severity = pattern.get("severity", "medium").upper()
        description = pattern.get("description", "No description available")

        section = f"""### Pattern {i}: {pattern_type}
- Confidence: {confidence:.0f}%
- Severity: {severity}
- Description: {description}"""

        # Add evidence if available
        evidence = pattern.get("evidence", [])
        if evidence and len(evidence) > 0:
            evidence_items = []
            for e in evidence[:3]:  # Limit to 3 evidence items
                if isinstance(e, dict):
                    evidence_items.append(str(e))
            if evidence_items:
                section += f"\n- Key Evidence: {'; '.join(evidence_items)}"

        sections.append(section)

    return "\n\n".join(sections)


def prepare_chain_inputs(
    kyc_data: Dict[str, Any],
    features: Dict[str, Any],
    patterns: List[Dict[str, Any]],
    additional_context: str = "",
) -> Dict[str, Any]:
    """Prepare inputs for the SAR chain."""
    return {
        "customer_name": kyc_data.get("name", "Unknown"),
        "account_number": kyc_data.get("account_number", "N/A"),
        "account_type": kyc_data.get("account_type", "Unknown"),
        "country": kyc_data.get("country", "US"),
        "occupation": kyc_data.get("occupation", "Not specified"),
        "risk_rating": kyc_data.get("risk_rating", "Unknown"),
        "pep_status": "Yes" if kyc_data.get("pep_status") else "No",
        "sanctions_match": "Yes" if kyc_data.get("sanctions_match") else "No",
        "transaction_count": features.get("transaction_count", 0),
        "date_range": f"{features.get('first_transaction_date', 'N/A')} to {features.get('last_transaction_date', 'N/A')}",
        "total_inflow": features.get("total_inflow", 0),
        "total_outflow": features.get("total_outflow", 0),
        "net_flow": features.get("net_flow", 0),
        "cross_border_count": features.get("cross_border_count", 0),
        "cross_border_percentage": features.get("cross_border_percentage", 0),
        "unique_counterparties": features.get("unique_counterparties", 0),
        "patterns_section": format_patterns_for_prompt(patterns),
        "additional_context": additional_context or "None",
    }


def generate_narrative_with_chain(
    kyc_data: Dict[str, Any],
    features: Dict[str, Any],
    patterns: List[Dict[str, Any]],
    audit_callback: Optional[AuditCallbackHandler] = None,
    additional_context: str = "",
) -> Optional[str]:
    """
    Generate SAR narrative using LangChain.

    Args:
        kyc_data: Customer KYC information
        features: Extracted transaction features
        patterns: Detected suspicious patterns
        audit_callback: Optional callback for audit logging
        additional_context: Optional additional context

    Returns:
        Generated narrative string or None if generation fails
    """
    chain = create_sar_chain(audit_callback)
    if chain is None:
        return None

    try:
        inputs = prepare_chain_inputs(kyc_data, features, patterns, additional_context)
        result = chain.invoke(inputs)

        narrative = result.get("text", "").strip()

        # Clean up any markdown formatting
        if narrative.startswith("```"):
            lines = narrative.split("\n")
            narrative = "\n".join(lines[1:-1] if lines[-1] == "```" else lines[1:])

        return narrative if narrative else None

    except Exception as e:
        print(f"Chain execution error: {e}")
        return None
