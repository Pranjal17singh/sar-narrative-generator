"""Context retrieval for narrative generation."""

from typing import List, Dict, Any

from backend.rag.vectorstore import query_similar
from backend.rag.embeddings import prepare_case_context_for_embedding
from backend.patterns.rules import get_pattern_description


def retrieve_relevant_context(
    kyc_data: Dict[str, Any],
    features: Dict[str, Any],
    patterns: List[Dict[str, Any]],
    n_results: int = 5,
) -> Dict[str, Any]:
    """
    Retrieve relevant regulatory context for narrative generation.

    Returns dict with:
        - regulatory_context: Retrieved regulatory language
        - pattern_descriptions: Detailed descriptions of detected patterns
        - retrieval_metadata: Information about what was retrieved
    """
    # Prepare query from case data
    case_context = prepare_case_context_for_embedding(kyc_data, features, patterns)

    # Query vector store
    results = query_similar(case_context, n_results=n_results)

    # Get pattern descriptions
    pattern_descriptions = []
    for pattern in patterns:
        pattern_type = pattern.get("pattern_type", "unknown")
        desc = get_pattern_description(pattern_type)
        pattern_descriptions.append({
            "type": pattern_type,
            "name": desc.get("name", pattern_type),
            "typology": desc.get("typology", ""),
            "indicators": desc.get("indicators", []),
            "detected_confidence": pattern.get("confidence", 0),
            "detected_severity": pattern.get("severity", "medium"),
            "detected_description": pattern.get("description", ""),
        })

    # Format regulatory context
    regulatory_context = "\n\n".join([
        f"[Source: {r['metadata'].get('source', 'unknown')}]\n{r['content']}"
        for r in results
    ])

    # Retrieval metadata for audit
    retrieval_metadata = {
        "query_used": case_context,
        "documents_retrieved": len(results),
        "sources": [
            {
                "source": r["metadata"].get("source"),
                "category": r["metadata"].get("category"),
                "similarity": round(r.get("similarity", 0), 3),
            }
            for r in results
        ],
    }

    return {
        "regulatory_context": regulatory_context,
        "pattern_descriptions": pattern_descriptions,
        "retrieval_metadata": retrieval_metadata,
    }


def get_fallback_context() -> str:
    """
    Get fallback regulatory context when vector store is unavailable.
    """
    return """
SAR Narrative Guidelines:

1. SUBJECT INFORMATION: Include full legal name, date of birth (if known),
   address, identification numbers, and relationship to the financial institution.

2. SUSPICIOUS ACTIVITY DESCRIPTION: Describe the activity that caused concern.
   Include dates, amounts, accounts, and any patterns observed.

3. NARRATIVE STRUCTURE:
   - Introduction: Identify the subject and reason for filing
   - Background: Account history and relationship with institution
   - Suspicious Activity: Detailed chronological description
   - Supporting Information: Additional relevant facts
   - Conclusion: Summary and any actions taken

4. LANGUAGE: Use clear, objective language. Avoid speculation.
   State facts and observations, not conclusions about criminality.

5. AMOUNTS: Include specific dollar amounts and transaction details.
   Aggregate totals where appropriate.

6. TIME PERIOD: Clearly state the time period covered by the SAR.

7. RED FLAGS: Document specific indicators that raised suspicion,
   referencing known typologies where applicable.
"""


def build_rag_prompt_context(
    kyc_data: Dict[str, Any],
    features: Dict[str, Any],
    patterns: List[Dict[str, Any]],
) -> Dict[str, str]:
    """
    Build complete context for the LLM prompt.

    Returns dict with formatted sections for prompt assembly.
    """
    # Use fallback context directly to avoid slow embedding operations
    regulatory_context = get_fallback_context()
    pattern_descs = [
        {
            "type": p.get("pattern_type", "unknown"),
            "name": p.get("pattern_type", "Unknown Pattern").replace("_", " ").title(),
            "detected_description": p.get("description", ""),
        }
        for p in patterns
    ]
    metadata = {"mode": "direct"}

    # Format customer info section
    customer_section = format_customer_info(kyc_data)

    # Format transaction summary section
    transaction_section = format_transaction_summary(features)

    # Format patterns section
    patterns_section = format_patterns_for_prompt(patterns, pattern_descs)

    return {
        "regulatory_context": regulatory_context or get_fallback_context(),
        "customer_info": customer_section,
        "transaction_summary": transaction_section,
        "patterns_detected": patterns_section,
        "retrieval_metadata": metadata,
    }


def format_customer_info(kyc_data: Dict[str, Any]) -> str:
    """Format KYC data for prompt."""
    if not kyc_data:
        return "Customer information not available."

    lines = [
        f"Customer Name: {kyc_data.get('name', 'Unknown')}",
        f"Customer ID: {kyc_data.get('customer_id', 'Unknown')}",
        f"Account Number: {kyc_data.get('account_number', 'Unknown')}",
        f"Account Type: {kyc_data.get('account_type', 'Unknown')}",
        f"Country: {kyc_data.get('country', 'Unknown')}",
    ]

    if kyc_data.get("occupation"):
        lines.append(f"Business/Occupation: {kyc_data['occupation']}")
    if kyc_data.get("risk_rating"):
        lines.append(f"Risk Rating: {kyc_data['risk_rating']}")
    if kyc_data.get("pep_status"):
        lines.append("PEP Status: Yes - Politically Exposed Person")
    if kyc_data.get("sanctions_match"):
        lines.append("Sanctions Match: Yes - Potential sanctions match identified")

    return "\n".join(lines)


def format_transaction_summary(features: Dict[str, Any]) -> str:
    """Format features as transaction summary for prompt."""
    if not features:
        return "Transaction data not available."

    lines = [
        f"Analysis Period: {features.get('first_transaction_date', 'Unknown')} to {features.get('last_transaction_date', 'Unknown')}",
        f"Total Transactions: {features.get('transaction_count', 0)}",
        f"Total Inflow: ${features.get('total_inflow', 0):,.2f}",
        f"Total Outflow: ${features.get('total_outflow', 0):,.2f}",
        f"Net Flow: ${features.get('net_flow', 0):,.2f}",
        f"Unique Counterparties: {features.get('unique_counterparties', 0)}",
        f"Average Transaction: ${features.get('avg_transaction_amount', 0):,.2f}",
        f"Maximum Transaction: ${features.get('max_transaction_amount', 0):,.2f}",
    ]

    if features.get("cross_border_count", 0) > 0:
        lines.append(f"Cross-Border Transactions: {features['cross_border_count']} ({features.get('cross_border_percentage', 0):.1f}%)")
        if features.get("cross_border_countries"):
            lines.append(f"Countries Involved: {', '.join(features['cross_border_countries'])}")

    if features.get("round_amount_count", 0) > 0:
        lines.append(f"Round Amount Transactions: {features['round_amount_count']}")

    if features.get("near_threshold_count", 0) > 0:
        lines.append(f"Near-Threshold Transactions ($8,000-$9,999): {features['near_threshold_count']}")

    return "\n".join(lines)


def format_patterns_for_prompt(
    patterns: List[Dict[str, Any]],
    pattern_descs: List[Dict[str, Any]],
) -> str:
    """Format detected patterns for prompt."""
    if not patterns:
        return "No specific suspicious patterns detected."

    lines = []

    for i, (pattern, desc) in enumerate(zip(patterns, pattern_descs), 1):
        lines.append(f"\n{i}. {desc.get('name', pattern.get('pattern_type', 'Unknown'))} "
                    f"(Confidence: {pattern.get('confidence', 0)*100:.0f}%, "
                    f"Severity: {pattern.get('severity', 'medium').upper()})")
        lines.append(f"   Description: {pattern.get('description', 'No description')}")

        if desc.get("typology"):
            lines.append(f"   Typology: {desc['typology']}")

        if pattern.get("recommendation"):
            lines.append(f"   Recommendation: {pattern['recommendation']}")

    return "\n".join(lines)
