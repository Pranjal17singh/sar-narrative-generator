"""Audit view component for displaying and editing SAR narrative."""

import streamlit as st
from typing import Dict, Any, List, Callable
from frontend.utils.api_client import get_client


def get_status_badge(status: str) -> str:
    """Get status badge with emoji."""
    badges = {
        "processing": "🔄 Processing",
        "review": "🟠 Review",
        "approved": "🟢 Approved",
        "exported": "✅ Exported",
    }
    return badges.get(status, status)


def get_severity_badge(severity: str) -> str:
    """Get severity badge with color."""
    badges = {
        "critical": "🔴",
        "high": "🔴",
        "medium": "🟡",
        "low": "🟢",
    }
    return badges.get(severity.lower(), "⚪")


def render_audit_header(audit: Dict[str, Any]):
    """Render audit header with customer name and status."""
    col1, col2 = st.columns([3, 1])

    with col1:
        st.title(f"Audit: {audit.get('customer_name', 'Unknown')}")

    with col2:
        status = audit.get("status", "processing")
        st.markdown(f"### {get_status_badge(status)}")


def render_detected_patterns(patterns: List[Dict[str, Any]]):
    """Render detected patterns section."""
    st.subheader("Detected Patterns")

    if not patterns:
        st.info("No suspicious patterns detected.")
        return

    for pattern in patterns:
        pattern_type = pattern.get("pattern_type", "unknown").replace("_", " ").title()
        confidence = pattern.get("confidence", 0) * 100
        severity = pattern.get("severity", "medium")
        description = pattern.get("description", "")

        severity_badge = get_severity_badge(severity)

        with st.container():
            col1, col2 = st.columns([3, 1])

            with col1:
                st.markdown(f"**{severity_badge} {pattern_type}**")
                st.caption(description[:200] + "..." if len(description) > 200 else description)

            with col2:
                st.metric("Confidence", f"{confidence:.0f}%")

            st.divider()


def render_features_summary(features: Dict[str, Any]):
    """Render extracted features summary."""
    with st.expander("Transaction Analysis Features"):
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric("Transactions", features.get("transaction_count", 0))
            st.metric("Counterparties", features.get("unique_counterparties", 0))

        with col2:
            st.metric("Total Inflow", f"${features.get('total_inflow', 0):,.2f}")
            st.metric("Total Outflow", f"${features.get('total_outflow', 0):,.2f}")

        with col3:
            st.metric("Cross-Border", f"{features.get('cross_border_percentage', 0):.1f}%")
            st.metric("Round Amounts", f"{features.get('round_amount_percentage', 0):.1f}%")

        with col4:
            st.metric("Date Range", f"{features.get('date_range_days', 0)} days")
            st.metric("Txns/Day", f"{features.get('transactions_per_day', 0):.1f}")


def render_narrative_section(
    audit: Dict[str, Any],
    on_save: Callable[[str], None],
    on_approve: Callable[[], None],
    on_export: Callable[[], None],
):
    """Render narrative editing section."""
    st.subheader("Generated Narrative")

    status = audit.get("status", "processing")
    audit_id = audit.get("id")

    # Determine which narrative to show
    if audit.get("final_narrative"):
        narrative = audit.get("final_narrative")
        st.success("This narrative has been approved.")
    elif audit.get("edited_narrative"):
        narrative = audit.get("edited_narrative")
        st.info("This is the edited version. Click Approve to finalize.")
    else:
        narrative = audit.get("generated_narrative", "")

    if not narrative:
        st.warning("Narrative generation in progress...")
        return

    # Narrative text area
    is_editable = status in ["review", "processing"]

    if is_editable:
        edited_narrative = st.text_area(
            "Edit Narrative",
            value=narrative,
            height=400,
            key=f"narrative_{audit_id}",
        )
    else:
        st.text_area(
            "Final Narrative",
            value=narrative,
            height=400,
            disabled=True,
        )

    # Action buttons
    st.markdown("---")
    col1, col2, col3 = st.columns(3)

    with col1:
        if is_editable:
            if st.button("💾 Save Draft", key="save_draft"):
                on_save(edited_narrative)

    with col2:
        if status == "review":
            if st.button("✅ Approve", key="approve", type="primary"):
                on_approve()
        elif status == "approved":
            st.success("Approved")

    with col3:
        if status in ["approved", "exported"]:
            if st.button("📄 Export PDF", key="export"):
                on_export()
        else:
            st.info("Approve to enable export")


def render_audit_view(
    audit: Dict[str, Any],
    on_back: Callable[[], None],
):
    """
    Render the full audit view page.

    Args:
        audit: Audit data with features, patterns, and narrative
        on_back: Callback when Back button is clicked
    """
    client = get_client()
    audit_id = audit.get("id")

    # Back button
    if st.button("← Back to Dashboard"):
        on_back()

    render_audit_header(audit)
    st.markdown("---")

    # Two column layout: Patterns | Narrative
    col1, col2 = st.columns([1, 2])

    with col1:
        render_detected_patterns(audit.get("patterns", []))
        render_features_summary(audit.get("features", {}))

    with col2:
        # Callbacks for narrative actions
        def on_save(narrative: str):
            result = client.edit_narrative(audit_id, narrative)
            if result.get("error"):
                st.error(f"Error saving: {result.get('message')}")
            else:
                st.success("Draft saved")
                st.rerun()

        def on_approve():
            result = client.approve_narrative(audit_id)
            if result.get("error"):
                st.error(f"Error approving: {result.get('message')}")
            else:
                st.success("Narrative approved")
                st.rerun()

        def on_export():
            pdf_content = client.export_pdf(audit_id)
            if pdf_content:
                customer_name = audit.get("customer_name", "report").replace(" ", "_")
                st.download_button(
                    "📥 Download PDF",
                    data=pdf_content,
                    file_name=f"SAR_{customer_name}.pdf",
                    mime="application/pdf",
                )
            else:
                st.error("Failed to generate PDF")

        render_narrative_section(audit, on_save, on_approve, on_export)

    # Audit trail section at bottom
    st.markdown("---")
    from frontend.components.audit_viewer import render_audit_trail, render_compliance_summary

    render_audit_trail(audit_id)
    render_compliance_summary(audit_id)
