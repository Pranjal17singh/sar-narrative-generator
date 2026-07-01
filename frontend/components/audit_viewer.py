"""Audit trail viewer component."""

import streamlit as st
from datetime import datetime
from frontend.utils.api_client import get_client


def render_audit_trail(audit_id: str):
    """Render audit trail for an audit."""
    client = get_client()

    st.subheader("Audit Trail")

    audit_logs = client.get_audit_logs(audit_id)

    if not audit_logs:
        st.info("No audit events recorded yet.")
        return

    # Summary metrics
    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("Total Events", len(audit_logs))

    with col2:
        event_types = set(log.get("event_type") for log in audit_logs)
        st.metric("Event Types", len(event_types))

    with col3:
        if audit_logs:
            first_time = audit_logs[0].get("timestamp", "")
            if first_time:
                if isinstance(first_time, str):
                    first_time = datetime.fromisoformat(first_time.replace("Z", "+00:00"))
                st.metric("First Event", first_time.strftime("%Y-%m-%d"))

    st.markdown("---")

    # Event timeline
    for log in audit_logs:
        render_audit_event(log)


def render_audit_event(log: dict):
    """Render single audit event."""
    event_type = log.get("event_type", "unknown")
    timestamp = log.get("timestamp", "")

    # Format timestamp
    if isinstance(timestamp, str):
        try:
            timestamp = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
            time_str = timestamp.strftime("%Y-%m-%d %H:%M:%S")
        except:
            time_str = timestamp
    else:
        time_str = str(timestamp)

    # Event type icons
    event_icons = {
        "audit_started": "🚀",
        "features_extracted": "🔍",
        "patterns_detected": "⚠️",
        "narrative_generated": "📝",
        "narrative_edited": "✏️",
        "narrative_approved": "✅",
        "pdf_exported": "📄",
        "json_exported": "📊",
    }

    icon = event_icons.get(event_type, "📌")

    with st.container():
        col1, col2 = st.columns([1, 4])

        with col1:
            st.caption(time_str)

        with col2:
            event_name = event_type.replace("_", " ").title()
            st.markdown(f"**{icon} {event_name}**")

            # Show details
            details = log.get("details", {})
            if details:
                render_event_details(event_type, details)

            # Show prompt/response for LLM events
            if log.get("prompt_sent") or log.get("llm_response"):
                with st.expander("View LLM Details"):
                    if log.get("prompt_sent"):
                        st.markdown("**Prompt Sent:**")
                        prompt = log["prompt_sent"]
                        st.code(prompt[:2000] + "..." if len(prompt) > 2000 else prompt)

                    if log.get("llm_response"):
                        st.markdown("**LLM Response:**")
                        st.text_area(
                            "Response",
                            value=log["llm_response"],
                            height=200,
                            disabled=True,
                            key=f"response_{log.get('id')}",
                        )

        st.divider()


def render_event_details(event_type: str, details: dict):
    """Render event-specific details."""
    if event_type == "audit_started":
        st.caption(f"Customer: {details.get('customer_name', 'N/A')}")
        st.caption(f"Transactions: {details.get('transaction_count', 0)}")

    elif event_type == "features_extracted":
        st.caption(f"Features: {details.get('feature_count', 0)}")
        st.caption(f"Total Inflow: ${details.get('total_inflow', 0):,.2f}")
        st.caption(f"Total Outflow: ${details.get('total_outflow', 0):,.2f}")

    elif event_type == "patterns_detected":
        patterns = details.get("patterns", [])
        count = details.get("pattern_count", len(patterns))
        st.caption(f"Patterns Found: {count}")
        for p in patterns[:5]:
            st.caption(f"• {p.replace('_', ' ').title()}")

    elif event_type == "narrative_generated":
        mode = details.get("generation_mode", "unknown")
        st.caption(f"Mode: {mode}")
        st.caption(f"Length: {details.get('narrative_length', 0)} chars")
        patterns = details.get("patterns", [])
        if patterns:
            st.caption(f"Patterns: {', '.join(patterns[:3])}")

    elif event_type == "narrative_edited":
        orig = details.get("original_length", 0)
        edited = details.get("edited_length", 0)
        st.caption(f"Original: {orig} chars → Edited: {edited} chars")

    elif event_type == "narrative_approved":
        notes = details.get("approver_notes")
        if notes:
            st.caption(f"Notes: {notes}")
        st.caption(f"Final Length: {details.get('narrative_length', 0)} chars")

    elif event_type in ["pdf_exported", "json_exported"]:
        st.caption(f"Exported: {details.get('exported_at', 'N/A')}")


def render_compliance_summary(audit_id: str):
    """Render compliance summary for the audit."""
    client = get_client()
    audit_logs = client.get_audit_logs(audit_id)

    if not audit_logs:
        return

    with st.expander("Compliance Summary"):
        event_types = [log.get("event_type") for log in audit_logs]

        checks = [
            ("Audit Started", "audit_started" in event_types),
            ("Features Extracted", "features_extracted" in event_types),
            ("Patterns Analyzed", "patterns_detected" in event_types),
            ("Narrative Generated", "narrative_generated" in event_types),
            ("Human Review", "narrative_edited" in event_types),
            ("Approved", "narrative_approved" in event_types),
            ("Exported", "pdf_exported" in event_types or "json_exported" in event_types),
        ]

        for label, passed in checks:
            icon = "✅" if passed else "⬜"
            st.write(f"{icon} {label}")
