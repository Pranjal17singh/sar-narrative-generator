"""Main Streamlit application for SAR Narrative Generator."""

import streamlit as st
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from frontend.utils.api_client import get_client
from frontend.components.customer_list import (
    render_customer_list,
    render_customer_metrics,
    render_risk_filter,
)
from frontend.components.customer_view import render_customer_view
from frontend.components.audit_view import render_audit_view

# Page config
st.set_page_config(
    page_title="SAR Narrative Generator",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom CSS
st.markdown("""
<style>
    .stMetric {
        background-color: #f0f2f6;
        padding: 10px;
        border-radius: 5px;
    }
    .stExpander {
        border: 1px solid #e0e0e0;
        border-radius: 5px;
    }
</style>
""", unsafe_allow_html=True)


# Initialize session state
if "current_page" not in st.session_state:
    st.session_state["current_page"] = "Dashboard"
if "selected_customer" not in st.session_state:
    st.session_state["selected_customer"] = None
if "selected_audit" not in st.session_state:
    st.session_state["selected_audit"] = None


def navigate_to(page: str, customer_id: str = None, audit_id: str = None):
    """Navigate to a page."""
    st.session_state["current_page"] = page
    if customer_id:
        st.session_state["selected_customer"] = customer_id
    if audit_id:
        st.session_state["selected_audit"] = audit_id


def main():
    """Main application entry point."""
    client = get_client()

    # Sidebar
    with st.sidebar:
        st.title("📊 SAR Generator")
        st.markdown("---")

        # System status
        health = client.health_check()
        if health.get("status") == "healthy":
            st.success("Backend Connected")
            if health.get("ollama_available"):
                st.info("🤖 LLM Mode Active")
            else:
                st.warning("📝 Template Mode (Ollama not available)")
        else:
            st.error("Backend Not Available")
            st.caption("Start backend: `uvicorn backend.main:app --reload`")

        st.markdown("---")

        # Navigation buttons
        st.subheader("Navigation")

        if st.button("📊 Dashboard", use_container_width=True,
                     type="primary" if st.session_state["current_page"] == "Dashboard" else "secondary"):
            navigate_to("Dashboard")
            st.rerun()

        if st.button("📋 Audits", use_container_width=True,
                     type="primary" if st.session_state["current_page"] == "Audits" else "secondary"):
            navigate_to("Audits")
            st.rerun()

        st.markdown("---")

        # Quick help
        with st.expander("Help"):
            st.markdown("""
            **Quick Start:**
            1. View customer list on Dashboard
            2. Select a customer to view profile
            3. Click "Start Audit" to analyze
            4. Review detected patterns
            5. Edit and approve narrative
            6. Export PDF

            **Seed Data:**
            Run `python data_samples/seed_data.py`
            """)

    # Main content area
    page = st.session_state["current_page"]

    if page == "Dashboard":
        render_dashboard(client)
    elif page == "Customer View":
        render_customer_page(client)
    elif page == "Audit View":
        render_audit_page(client)
    elif page == "Audits":
        render_audits_list(client)


def render_dashboard(client):
    """Render main dashboard with customer list."""
    st.title("SAR Narrative Generator")
    st.markdown("AI-assisted compliance system for generating Suspicious Activity Report narratives.")

    # Get customers
    customers = client.list_customers()

    # Metrics row
    render_customer_metrics(customers)

    st.markdown("---")

    # Filter row
    col1, col2 = st.columns([1, 3])
    with col1:
        risk_filter = render_risk_filter()

    st.markdown("---")

    # Customer list
    def on_view_customer(customer_id: str):
        navigate_to("Customer View", customer_id=customer_id)
        st.rerun()

    render_customer_list(customers, on_view_customer, risk_filter)


def render_customer_page(client):
    """Render customer detail page."""
    customer_id = st.session_state.get("selected_customer")

    if not customer_id:
        st.warning("No customer selected.")
        if st.button("Go to Dashboard"):
            navigate_to("Dashboard")
            st.rerun()
        return

    # Fetch customer data
    customer = client.get_customer(customer_id)

    if customer.get("error"):
        st.error(f"Error loading customer: {customer.get('message')}")
        if st.button("Go to Dashboard"):
            navigate_to("Dashboard")
            st.rerun()
        return

    def on_back():
        navigate_to("Dashboard")
        st.rerun()

    def on_start_audit(cust_id: str):
        with st.spinner("Starting audit and generating narrative..."):
            result = client.start_audit(cust_id)

        if result.get("error"):
            st.error(f"Error starting audit: {result.get('message')}")
        else:
            st.success(result.get("message", "Audit started"))
            audit_id = result.get("audit_id")
            navigate_to("Audit View", audit_id=audit_id)
            st.rerun()

    render_customer_view(customer, on_start_audit, on_back)


def render_audit_page(client):
    """Render audit detail page."""
    audit_id = st.session_state.get("selected_audit")

    if not audit_id:
        st.warning("No audit selected.")
        if st.button("Go to Dashboard"):
            navigate_to("Dashboard")
            st.rerun()
        return

    # Fetch audit data
    audit = client.get_audit(audit_id)

    if audit.get("error"):
        st.error(f"Error loading audit: {audit.get('message')}")
        if st.button("Go to Dashboard"):
            navigate_to("Dashboard")
            st.rerun()
        return

    def on_back():
        navigate_to("Dashboard")
        st.rerun()

    render_audit_view(audit, on_back)


def render_audits_list(client):
    """Render list of all audits."""
    st.title("All Audits")

    # Status filter
    status_filter = st.selectbox(
        "Filter by Status",
        options=["All", "processing", "review", "approved", "exported"],
    )

    audits = client.list_audits(
        status=status_filter if status_filter != "All" else None
    )

    if not audits:
        st.info("No audits found.")
        return

    # Metrics
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Audits", len(audits))
    with col2:
        review = len([a for a in audits if a.get("status") == "review"])
        st.metric("In Review", review)
    with col3:
        approved = len([a for a in audits if a.get("status") == "approved"])
        st.metric("Approved", approved)
    with col4:
        exported = len([a for a in audits if a.get("status") == "exported"])
        st.metric("Exported", exported)

    st.markdown("---")

    # Audit list
    for audit in audits:
        with st.container():
            col1, col2, col3, col4 = st.columns([3, 1, 1, 1])

            with col1:
                st.markdown(f"**{audit.get('customer_name', 'Unknown')}**")
                st.caption(f"Audit ID: {audit.get('id', '')[:8]}...")

            with col2:
                status = audit.get("status", "processing")
                status_badges = {
                    "processing": "🔄 Processing",
                    "review": "🟠 Review",
                    "approved": "🟢 Approved",
                    "exported": "✅ Exported",
                }
                st.write(status_badges.get(status, status))

            with col3:
                created = audit.get("created_at", "")
                if created:
                    from datetime import datetime
                    try:
                        dt = datetime.fromisoformat(created.replace("Z", "+00:00"))
                        created = dt.strftime("%Y-%m-%d")
                    except:
                        pass
                st.write(created)

            with col4:
                if st.button("Open", key=f"open_audit_{audit.get('id')}"):
                    navigate_to("Audit View", audit_id=audit.get("id"))
                    st.rerun()

            st.divider()


if __name__ == "__main__":
    main()
