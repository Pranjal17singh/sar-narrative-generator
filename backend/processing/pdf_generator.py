"""PDF generation for SAR reports."""

from typing import Dict, Any, List
from datetime import datetime
from io import BytesIO

from fpdf import FPDF


class SARPDF(FPDF):
    """Custom PDF class for SAR reports."""

    def __init__(self):
        super().__init__()
        self.set_auto_page_break(auto=True, margin=15)

    def header(self):
        """Page header."""
        self.set_font("Helvetica", "B", 10)
        self.cell(0, 10, "SUSPICIOUS ACTIVITY REPORT", align="C", new_x="LMARGIN", new_y="NEXT")
        self.set_font("Helvetica", "", 8)
        self.cell(0, 5, "CONFIDENTIAL - FOR AUTHORIZED USE ONLY", align="C", new_x="LMARGIN", new_y="NEXT")
        self.ln(5)

    def footer(self):
        """Page footer."""
        self.set_y(-15)
        self.set_font("Helvetica", "I", 8)
        self.cell(0, 10, f"Page {self.page_no()}/{{nb}}", align="C")

    def section_title(self, title: str):
        """Add section title."""
        self.set_font("Helvetica", "B", 11)
        self.set_fill_color(240, 240, 240)
        self.cell(0, 8, title, fill=True, new_x="LMARGIN", new_y="NEXT")
        self.ln(2)

    def add_field(self, label: str, value: str):
        """Add labeled field."""
        self.set_font("Helvetica", "B", 9)
        self.cell(50, 6, f"{label}:")
        self.set_font("Helvetica", "", 9)
        self.multi_cell(0, 6, str(value) if value else "N/A")

    def add_narrative(self, text: str):
        """Add narrative text with proper formatting."""
        self.set_font("Helvetica", "", 10)
        # Handle encoding issues
        text = text.encode("latin-1", "replace").decode("latin-1")
        self.multi_cell(0, 5, text)


def generate_sar_pdf(
    case_name: str,
    case_id: str,
    narrative: str,
    kyc_data: Dict[str, Any],
    features: Dict[str, Any],
    patterns: List[Dict[str, Any]],
    created_at: datetime = None,
) -> bytes:
    """
    Generate PDF for SAR report.

    Returns PDF as bytes.
    """
    pdf = SARPDF()
    pdf.alias_nb_pages()
    pdf.add_page()

    # Title
    pdf.set_font("Helvetica", "B", 14)
    pdf.cell(0, 10, f"Case: {case_name}", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 9)
    pdf.cell(0, 5, f"Case ID: {case_id}", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 5, f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(10)

    # Subject Information
    pdf.section_title("SUBJECT INFORMATION")
    pdf.add_field("Name", kyc_data.get("name"))
    pdf.add_field("Customer ID", kyc_data.get("customer_id"))
    pdf.add_field("Account Number", kyc_data.get("account_number"))
    pdf.add_field("Account Type", kyc_data.get("account_type"))
    pdf.add_field("Country", kyc_data.get("country"))
    pdf.add_field("Business/Occupation", kyc_data.get("occupation"))
    pdf.add_field("Risk Rating", kyc_data.get("risk_rating"))

    if kyc_data.get("pep_status"):
        pdf.set_font("Helvetica", "B", 9)
        pdf.set_text_color(255, 0, 0)
        pdf.cell(0, 6, "** POLITICALLY EXPOSED PERSON **", new_x="LMARGIN", new_y="NEXT")
        pdf.set_text_color(0, 0, 0)

    if kyc_data.get("sanctions_match"):
        pdf.set_font("Helvetica", "B", 9)
        pdf.set_text_color(255, 0, 0)
        pdf.cell(0, 6, "** POTENTIAL SANCTIONS MATCH **", new_x="LMARGIN", new_y="NEXT")
        pdf.set_text_color(0, 0, 0)

    pdf.ln(5)

    # Transaction Summary
    pdf.section_title("TRANSACTION SUMMARY")

    pdf.add_field("Review Period",
                  f"{features.get('first_transaction_date', 'N/A')} to {features.get('last_transaction_date', 'N/A')}")
    pdf.add_field("Total Transactions", str(features.get("transaction_count", 0)))
    pdf.add_field("Total Inflow", f"${features.get('total_inflow', 0):,.2f}")
    pdf.add_field("Total Outflow", f"${features.get('total_outflow', 0):,.2f}")
    pdf.add_field("Net Flow", f"${features.get('net_flow', 0):,.2f}")
    pdf.add_field("Unique Counterparties", str(features.get("unique_counterparties", 0)))
    pdf.add_field("Cross-Border Transactions", str(features.get("cross_border_count", 0)))

    if features.get("cross_border_countries"):
        pdf.add_field("Countries", ", ".join(features["cross_border_countries"]))

    pdf.ln(5)

    # Detected Patterns
    pdf.section_title("SUSPICIOUS PATTERNS DETECTED")

    if patterns:
        for i, pattern in enumerate(patterns, 1):
            pdf.set_font("Helvetica", "B", 10)
            pattern_type = pattern.get("pattern_type", "unknown").replace("_", " ").title()
            severity = pattern.get("severity", "medium").upper()
            confidence = pattern.get("confidence", 0) * 100

            pdf.cell(0, 6, f"{i}. {pattern_type} (Severity: {severity}, Confidence: {confidence:.0f}%)",
                     new_x="LMARGIN", new_y="NEXT")

            pdf.set_font("Helvetica", "", 9)
            description = pattern.get("description", "No description")
            # Handle encoding
            description = description.encode("latin-1", "replace").decode("latin-1")
            pdf.multi_cell(0, 5, description)

            if pattern.get("recommendation"):
                pdf.set_font("Helvetica", "I", 9)
                rec = pattern["recommendation"].encode("latin-1", "replace").decode("latin-1")
                pdf.multi_cell(0, 5, f"Recommendation: {rec}")

            pdf.ln(3)
    else:
        pdf.set_font("Helvetica", "", 9)
        pdf.cell(0, 6, "No specific suspicious patterns detected.", new_x="LMARGIN", new_y="NEXT")

    pdf.ln(5)

    # Narrative
    pdf.section_title("SAR NARRATIVE")
    pdf.add_narrative(narrative or "No narrative generated.")

    pdf.ln(10)

    # Footer disclaimer
    pdf.section_title("DISCLAIMER")
    pdf.set_font("Helvetica", "I", 8)
    disclaimer = (
        "This Suspicious Activity Report is filed pursuant to 31 U.S.C. 5318(g) and 31 CFR 1020.320. "
        "This report is confidential. Unauthorized disclosure is prohibited by law. "
        "The filing of this report does not constitute a determination that money laundering or "
        "other illegal activity has occurred. This report documents activity that may warrant "
        "further investigation."
    )
    pdf.multi_cell(0, 4, disclaimer)

    # Signature block
    pdf.ln(10)
    pdf.set_font("Helvetica", "", 9)
    pdf.cell(0, 6, "Prepared by: _____________________________", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 6, "Date: _____________________________", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 6, "Approved by: _____________________________", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 6, "Date: _____________________________", new_x="LMARGIN", new_y="NEXT")

    # Output
    return pdf.output()
