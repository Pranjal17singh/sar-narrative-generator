"""Case detail view component."""

import streamlit as st
import pandas as pd
from datetime import datetime


def render_case_header(case: dict):
    """Render case header with status."""
    col1, col2, col3 = st.columns([3, 1, 1])

    with col1:
        st.title(f"Case: {case.get('name', 'Unknown')}")

    with col2:
        status = case.get("status", "pending")
        status_colors = {
            "pending": "🔵",
            "processing": "🟡",
            "review": "🟠",
            "approved": "🟢",
            "exported": "✅",
        }
        st.metric("Status", f"{status_colors.get(status, '⚪')} {status.upper()}")

    with col3:
        created = case.get("created_at", "")
        if created:
            if isinstance(created, str):
                created = datetime.fromisoformat(created.replace("Z", "+00:00"))
            st.metric("Created", created.strftime("%Y-%m-%d"))


def render_transaction_summary(case: dict):
    """Render transaction data summary."""
    st.subheader("Transaction Summary")

    transactions = case.get("transaction_data", [])
    features = case.get("features", {})

    if not transactions:
        st.info("No transaction data uploaded yet.")
        return

    # Summary metrics
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("Total Transactions", features.get("transaction_count", len(transactions)))

    with col2:
        inflow = features.get("total_inflow", 0)
        st.metric("Total Inflow", f"${inflow:,.2f}")

    with col3:
        outflow = features.get("total_outflow", 0)
        st.metric("Total Outflow", f"${outflow:,.2f}")

    with col4:
        counterparties = features.get("unique_counterparties", 0)
        st.metric("Counterparties", counterparties)

    # Transaction table
    with st.expander("View Transactions", expanded=False):
        df = pd.DataFrame(transactions)
        if not df.empty:
            # Format columns
            if "amount" in df.columns:
                df["amount"] = df["amount"].apply(lambda x: f"${x:,.2f}")
            if "date" in df.columns:
                df["date"] = pd.to_datetime(df["date"]).dt.strftime("%Y-%m-%d %H:%M")

            st.dataframe(df, use_container_width=True)


def render_kyc_summary(case: dict):
    """Render KYC data summary."""
    kyc = case.get("kyc_data", {})

    if not kyc:
        st.info("No KYC data uploaded yet.")
        return

    st.subheader("Customer Information")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown(f"**Name:** {kyc.get('name', 'N/A')}")
        st.markdown(f"**Customer ID:** {kyc.get('customer_id', 'N/A')}")
        st.markdown(f"**Account:** {kyc.get('account_number', 'N/A')}")
        st.markdown(f"**Account Type:** {kyc.get('account_type', 'N/A')}")

    with col2:
        st.markdown(f"**Country:** {kyc.get('country', 'N/A')}")
        st.markdown(f"**Business:** {kyc.get('occupation', 'N/A')}")
        st.markdown(f"**Risk Rating:** {kyc.get('risk_rating', 'N/A')}")

        if kyc.get("pep_status"):
            st.warning("⚠️ PEP Status: Yes")
        if kyc.get("sanctions_match"):
            st.error("🚨 Sanctions Match: Yes")


def render_features_detail(case: dict):
    """Render detailed features breakdown."""
    features = case.get("features", {})

    if not features:
        return

    with st.expander("Detailed Features", expanded=False):
        col1, col2, col3 = st.columns(3)

        with col1:
            st.markdown("**Volume Metrics**")
            st.write(f"Avg Transaction: ${features.get('avg_transaction_amount', 0):,.2f}")
            st.write(f"Max Transaction: ${features.get('max_transaction_amount', 0):,.2f}")
            st.write(f"Transactions/Day: {features.get('transactions_per_day', 0):.1f}")

        with col2:
            st.markdown("**Time Patterns**")
            st.write(f"Date Range: {features.get('date_range_days', 0)} days")
            st.write(f"Weekend Txns: {features.get('weekend_transaction_count', 0)}")
            st.write(f"Off-Hours Txns: {features.get('off_hours_transaction_count', 0)}")

        with col3:
            st.markdown("**Risk Indicators**")
            st.write(f"Cross-Border: {features.get('cross_border_count', 0)}")
            st.write(f"Round Amounts: {features.get('round_amount_count', 0)}")
            st.write(f"Near-Threshold: {features.get('near_threshold_count', 0)}")

        # Countries involved
        countries = features.get("cross_border_countries", [])
        if countries:
            st.markdown(f"**Countries Involved:** {', '.join(countries)}")


def render_patterns(case: dict):
    """Render detected patterns."""
    patterns = case.get("patterns", [])

    st.subheader("Detected Patterns")

    if not patterns:
        st.info("No suspicious patterns detected.")
        return

    for pattern in patterns:
        severity = pattern.get("severity", "medium")
        severity_colors = {
            "low": "🟢",
            "medium": "🟡",
            "high": "🟠",
            "critical": "🔴",
        }

        pattern_type = pattern.get("pattern_type", "unknown").replace("_", " ").title()
        confidence = pattern.get("confidence", 0) * 100

        with st.container():
            col1, col2 = st.columns([3, 1])

            with col1:
                st.markdown(
                    f"### {severity_colors.get(severity, '⚪')} {pattern_type}"
                )

            with col2:
                st.metric("Confidence", f"{confidence:.0f}%")

            st.write(pattern.get("description", "No description available"))

            if pattern.get("recommendation"):
                st.info(f"💡 **Recommendation:** {pattern['recommendation']}")

            st.divider()
