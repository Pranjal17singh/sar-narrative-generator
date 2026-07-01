"""Customer list component for the dashboard."""

import streamlit as st
from typing import List, Dict, Any, Callable


def get_risk_badge(risk_rating: str) -> str:
    """Get risk badge emoji based on risk rating."""
    badges = {
        "High": "🔴",
        "Medium": "🟡",
        "Low": "🟢",
    }
    return badges.get(risk_rating, "⚪")


def render_customer_list(
    customers: List[Dict[str, Any]],
    on_view_customer: Callable[[str], None],
    risk_filter: str = None,
):
    """
    Render the customer list dashboard.

    Args:
        customers: List of customer data
        on_view_customer: Callback when "View" button is clicked
        risk_filter: Optional filter for risk rating
    """
    st.subheader("Customers")

    if not customers:
        st.info("No customers found. Run the seed script to populate data.")
        st.code("python data_samples/seed_data.py", language="bash")
        return

    # Header row
    header_cols = st.columns([0.5, 2, 1.5, 1, 1, 1])
    with header_cols[0]:
        st.markdown("**Risk**")
    with header_cols[1]:
        st.markdown("**Name**")
    with header_cols[2]:
        st.markdown("**Account**")
    with header_cols[3]:
        st.markdown("**Country**")
    with header_cols[4]:
        st.markdown("**Txns**")
    with header_cols[5]:
        st.markdown("**Action**")

    st.divider()

    # Customer rows
    for customer in customers:
        # Apply filter if set
        if risk_filter and risk_filter != "All":
            if customer.get("risk_rating") != risk_filter:
                continue

        cols = st.columns([0.5, 2, 1.5, 1, 1, 1])

        with cols[0]:
            risk_badge = get_risk_badge(customer.get("risk_rating", ""))
            st.write(risk_badge)

        with cols[1]:
            name = customer.get("name", "Unknown")
            st.write(name)
            # Show PEP/Sanctions badges if applicable
            badges = []
            if customer.get("pep_status"):
                badges.append("👔 PEP")
            if customer.get("sanctions_match"):
                badges.append("⚠️ Sanctions")
            if badges:
                st.caption(" | ".join(badges))

        with cols[2]:
            st.write(customer.get("account_number", "N/A"))

        with cols[3]:
            st.write(customer.get("country", "US"))

        with cols[4]:
            txn_count = customer.get("transaction_count", 0)
            st.write(f"{txn_count}")

        with cols[5]:
            if st.button("View", key=f"view_{customer.get('id')}"):
                on_view_customer(customer.get("id"))

        st.divider()


def render_customer_metrics(customers: List[Dict[str, Any]]):
    """Render customer metrics summary."""
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("Total Customers", len(customers))

    with col2:
        high_risk = len([c for c in customers if c.get("risk_rating") == "High"])
        st.metric("High Risk", high_risk)

    with col3:
        pep_count = len([c for c in customers if c.get("pep_status")])
        st.metric("PEP Status", pep_count)

    with col4:
        sanctions = len([c for c in customers if c.get("sanctions_match")])
        st.metric("Sanctions Match", sanctions)


def render_risk_filter() -> str:
    """Render risk filter selector and return selected value."""
    return st.selectbox(
        "Filter by Risk",
        options=["All", "High", "Medium", "Low"],
        key="risk_filter",
    )
