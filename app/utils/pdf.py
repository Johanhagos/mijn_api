from fpdf import FPDF
import requests
from io import BytesIO
import tempfile
import os


def generate_invoice_pdf(invoice) -> str:
    pdf = FPDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.set_font("Arial", "B", 16)

    # Add logo if available (URL or file path)
    if getattr(invoice, "seller_logo_url", None):
        logo_url = invoice.seller_logo_url
        try:
            if logo_url.startswith("http://") or logo_url.startswith("https://"):
                resp = requests.get(logo_url, timeout=5)
                resp.raise_for_status()
                suffix = os.path.splitext(logo_url)[1] or ".png"
                with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tf:
                    tf.write(resp.content)
                    tmp_path = tf.name
                try:
                    pdf.image(tmp_path, x=10, y=8, w=40)
                finally:
                    try:
                        os.unlink(tmp_path)
                    except Exception:
                        pass
            else:
                # assume local path
                pdf.image(logo_url, x=10, y=8, w=40)
        except Exception:
            # best-effort: continue without logo
            pass

    pdf.ln(20)
    pdf.cell(0, 10, f"Invoice #{invoice.invoice_number}", ln=True)
    pdf.set_font("Arial", "", 12)
    pdf.cell(0, 8, f"Order Number: {invoice.order_number}", ln=True)
    pdf.cell(0, 8, f"Date: {invoice.invoice_date}", ln=True)

    pdf.ln(6)
    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 8, "Seller", ln=True)
    pdf.set_font("Arial", "", 11)
    pdf.cell(0, 6, f"{invoice.seller_name}", ln=True)
    pdf.multi_cell(0, 6, f"{invoice.seller_address}")
    pdf.cell(0, 6, f"VAT: {invoice.seller_vat_number}", ln=True)

    pdf.ln(4)
    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 8, "Customer", ln=True)
    pdf.set_font("Arial", "", 11)
    pdf.cell(0, 6, f"{invoice.customer_name}", ln=True)
    pdf.multi_cell(0, 6, f"{invoice.customer_address}")
    try:
        ctype = invoice.customer_type.value if hasattr(invoice.customer_type, "value") else str(invoice.customer_type)
    except Exception:
        ctype = str(invoice.customer_type)
    if ctype == "business" and invoice.customer_vat_number:
        pdf.cell(0, 6, f"VAT: {invoice.customer_vat_number}", ln=True)

    pdf.ln(6)
    pdf.set_font("Arial", "", 12)
    pdf.cell(0, 6, f"Subtotal: {invoice.subtotal}", ln=True)
    pdf.cell(0, 6, f"VAT ({invoice.vat_rate}%): {invoice.vat_total}", ln=True)
    pdf.cell(0, 6, f"Total: {invoice.total}", ln=True)

    pdf.ln(5)
    pdf.set_font("Arial", "I", 10)
    try:
        ps = invoice.payment_system.value if hasattr(invoice.payment_system, "value") else str(invoice.payment_system)
    except Exception:
        ps = str(getattr(invoice, "payment_system", "web2"))
    pdf.cell(0, 10, f"Payment system: {ps.upper()}", ln=True)

    try:
        if (ps == "web3" or (hasattr(invoice, "payment_system") and getattr(invoice.payment_system, "value", None) == "web3")) and getattr(invoice, "blockchain_tx_id", None):
            pdf.multi_cell(0, 10, f"Blockchain / Smart Contract ID: {invoice.blockchain_tx_id}")
    except Exception:
        pass

    filename = f"invoice_{invoice.invoice_number}.pdf"
    pdf.output(filename)
    return filename
