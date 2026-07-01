"""Customer view component for profile and transactions."""

import streamlit as st
from typing import Dict, Any, List, Callable
from datetime import datetime


def get_risk_badge(risk_rating: str) -> str:
    """Get risk badge emoji based on risk rating."""
    badges = {
        "High": "🔴 High",
        "Medium": "🟡 Medium",
        "Low": "🟢 Low",
    }
    return badges.get(risk_rating, "⚪ Unknown")


def render_customer_header(customer: Dict[str, Any]):
    """Render customer header with name and risk badge."""
    col1, col2 = st.columns([3, 1])

    with col1:
        st.title(f"Customer: {customer.get('name', 'Unknown')}")

    with col2:
        risk_badge = get_risk_badge(customer.get("risk_rating", ""))
        st.markdown(f"### {risk_badge}")


def render_customer_profile(customer: Dict[str, Any]):
    """Render customer profile information."""
    st.subheader("Profile Information")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown(f"**Account:** {customer.get('account_number', 'N/A')}")
        st.markdown(f"**Type:** {customer.get('account_type', 'N/A')}")

    with col2:
        st.markdown(f"**Country:** {customer.get('country', 'US')}")
        st.markdown(f"**Occupation:** {customer.get('occupation', 'N/A')}")

    with col3:
        pep_status = "Yes" if customer.get("pep_status") else "No"
        sanctions_status = "Yes" if customer.get("sanctions_match") else "No"
        st.markdown(f"**PEP Status:** {pep_status}")
        st.markdown(f"**Sanctions Match:** {sanctions_status}")

    # Risk indicators warning
    if customer.get("pep_status") or customer.get("sanctions_match") or customer.get("risk_rating") == "High":
        st.warning("This customer has elevated risk indicators. Review carefully before proceeding.")


def render_transaction_table(transactions: List[Dict[str, Any]]):
    """Render transaction history table."""
    st.subheader(f"Transaction History ({len(transactions)} transactions)")

    if not transactions:
        st.info("No transactions found for this customer.")
        return

    # Calculate summary metrics
    credits = [t for t in transactions if t.get("transaction_type") == "credit"]
    debits = [t for t in transactions if t.get("transaction_type") == "debit"]

    total_credits = sum(t.get("amount", 0) for t in credits)
    total_debits = sum(t.get("amount", 0) for t in debits)

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Transactions", len(transactions))
    with col2:
        st.metric("Total Credits", f"${total_credits:,.2f}")
    with col3:
        st.metric("Total Debits", f"${total_debits:,.2f}")
    with col4:
        st.metric("Net Flow", f"${total_credits - total_debits:,.2f}")

    st.markdown("---")

    # Table header
    header_cols = st.columns([1.2, 1.2, 0.8, 1.5, 1.2])
    with header_cols[0]:
        st.markdown("**Date**")
    with header_cols[1]:
        st.markdown("**Amount**")
    with header_cols[2]:
        st.markdown("**Type**")
    with header_cols[3]:
        st.markdown("**Counterparty**")
    with header_cols[4]:
        st.markdown("**Country**")

    # Limit to first 20 transactions for display
    display_transactions = transactions[:20]

    for txn in display_transactions:
        cols = st.columns([1.2, 1.2, 0.8, 1.5, 1.2])

        with cols[0]:
            date_str = txn.get("date", "")
            if date_str:
                try:
                    dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
                    date_str = dt.strftime("%b %d, %Y")
                except:
                    pass
            st.write(date_str)

        with cols[1]:
            amount = txn.get("amount", 0)
            st.write(f"${amount:,.2f}")

        with cols[2]:
            txn_type = txn.get("transaction_type", "")
            if txn_type == "credit":
                st.write("⬆️ Credit")
            else:
                st.write("⬇️ Debit")

        with cols[3]:
            st.write(txn.get("counterparty", "N/A"))

        with cols[4]:
            country = txn.get("counterparty_country", "N/A")
            # Flag high-risk countries
            high_risk = ["Cayman Islands", "Panama", "UAE", "Hong Kong"]
            if country in high_risk:
                st.write(f"⚠️ {country}")
            else:
                st.write(country)

    if len(transactions) > 20:
        st.info(f"Showing first 20 of {len(transactions)} transactions")


def render_start_audit_button(
    customer_id: str,
    on_start_audit: Callable[[str], None],
):
    """Render the Start Audit button."""
    st.markdown("---")

    col1, col2, col3 = st.columns([1, 2, 1])

    with col2:
        if st.button(
            "🔍 START AUDIT",
            key=f"start_audit_{customer_id}",
            type="primary",
            use_container_width=True,
        ):
            on_start_audit(customer_id)


def render_customer_view(
    customer: Dict[str, Any],
    on_start_audit: Callable[[str], None],
    on_back: Callable[[], None],
):
    """
    Render the full customer view page.

    Args:
        customer: Customer data with transactions
        on_start_audit: Callback when Start Audit is clicked
        on_back: Callback when Back button is clicked
    """
    # Back button
    if st.button("← Back to Dashboard"):
        on_back()

    render_customer_header(customer)
    st.markdown("---")

    render_customer_profile(customer)
    st.markdown("---")

    transactions = customer.get("transactions", [])
    render_transaction_table(transactions)

    render_start_audit_button(customer.get("id"), on_start_audit)
