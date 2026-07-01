"""Narrative editor component."""

import streamlit as st
from frontend.utils.api_client import get_client


def render_narrative_section(case: dict):
    """Render narrative generation and editing section."""
    client = get_client()
    case_id = case.get("id")

    st.subheader("SAR Narrative")

    # Check for existing narrative
    generated = case.get("generated_narrative")
    edited = case.get("edited_narrative")
    final = case.get("final_narrative")

    current_narrative = final or edited or generated

    # Generation controls
    if not case.get("transaction_data"):
        st.warning("Upload transaction data before generating narrative.")
        return

    col1, col2 = st.columns([1, 3])

    with col1:
        # Check generation mode
        health = client.health_check()
        mode = "LLM" if health.get("ollama_available") else "Template"
        mode_color = "🟢" if health.get("ollama_available") else "🟡"
        st.caption(f"{mode_color} Mode: {mode}")

    with col2:
        generate_btn = st.button(
            "Generate Narrative" if not current_narrative else "Regenerate Narrative",
            key="generate_btn",
            type="primary" if not current_narrative else "secondary",
        )

    if generate_btn:
        with st.spinner("Generating narrative... This may take a moment."):
            result = client.generate_narrative(case_id)

        if result.get("error"):
            st.error(f"Error: {result.get('message')}")
        else:
            st.success(f"Narrative generated ({result.get('generation_mode', 'unknown')} mode)")
            st.rerun()

    if not current_narrative:
        st.info("Click 'Generate Narrative' to create the SAR narrative.")
        return

    # Display and edit narrative
    st.markdown("---")

    # Editor
    edited_text = st.text_area(
        "Edit Narrative",
        value=current_narrative,
        height=400,
        key="narrative_editor",
    )

    # Action buttons
    col1, col2, col3 = st.columns(3)

    with col1:
        if st.button("Save Draft", key="save_draft"):
            result = client.edit_narrative(case_id, edited_text)
            if result.get("error"):
                st.error(f"Error: {result.get('message')}")
            else:
                st.success("Draft saved")
                st.rerun()

    with col2:
        status = case.get("status")
        if status != "approved":
            if st.button("Approve Narrative", key="approve_btn", type="primary"):
                # Save current edits first
                if edited_text != current_narrative:
                    client.edit_narrative(case_id, edited_text)

                result = client.approve_narrative(case_id)
                if result.get("error"):
                    st.error(f"Error: {result.get('message')}")
                else:
                    st.success("Narrative approved!")
                    st.rerun()
        else:
            st.success("✅ Narrative Approved")

    with col3:
        # Word count
        word_count = len(edited_text.split())
        st.metric("Word Count", word_count)


def render_narrative_preview(case: dict):
    """Render read-only narrative preview."""
    final = case.get("final_narrative")
    edited = case.get("edited_narrative")
    generated = case.get("generated_narrative")

    narrative = final or edited or generated

    if not narrative:
        return

    with st.expander("Preview Narrative", expanded=False):
        st.markdown(narrative)


def render_generation_info():
    """Render information about narrative generation."""
    with st.expander("About Narrative Generation"):
        st.markdown("""
        **Generation Modes:**

        - **LLM Mode** 🟢: Uses Ollama with Mistral 7B to generate sophisticated,
          context-aware narratives based on regulatory guidance and detected patterns.

        - **Template Mode** 🟡: Uses rule-based templates when Ollama is not available.
          Still produces compliant narratives but with less contextual nuance.

        **Narrative Structure:**
        1. Introduction with subject identification
        2. Customer background information
        3. Transaction activity summary
        4. Suspicious pattern descriptions
        5. Red flags and indicators
        6. Conclusion and recommendations

        **Tips:**
        - Review and edit the generated narrative before approval
        - Ensure all facts are accurate
        - Add any additional context known to the analyst
        - Remove any speculative language
        """)
