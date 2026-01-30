from fpdf import FPDF
from fpdf.enums import XPos, YPos
import requests
from io import BytesIO
import tempfile
import os
import textwrap

try:
    import qrcode
except Exception:
    qrcode = None


def generate_invoice_pdf(invoice) -> str:
    pdf = FPDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.set_font("Helvetica", "B", 16)

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
    pdf.cell(0, 10, f"Invoice #{invoice.invoice_number}", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_font("Helvetica", "", 12)
    pdf.cell(0, 8, f"Order Number: {invoice.order_number}", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.cell(0, 8, f"Date: {invoice.invoice_date}", new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    pdf.ln(6)
    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 8, "Seller", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_font("Helvetica", "", 11)
    pdf.cell(0, 6, f"{invoice.seller_name}", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.multi_cell(0, 6, f"{invoice.seller_address}")

    # Seller VAT and optional VIES validation
    seller_vat = getattr(invoice, "seller_vat_number", "") or ""
    sv_status = None
    if hasattr(invoice, "seller_vat_validated"):
        sv_status = "validated" if invoice.seller_vat_validated else "unvalidated"
    else:
        if seller_vat:
            try:
                from zeep import Client
                wsdl = "https://ec.europa.eu/taxation_customs/vies/checkVatService.wsdl"
                client = Client(wsdl=wsdl)
                country = seller_vat[:2]
                number = seller_vat[2:]
                res = client.service.checkVat(countryCode=country, vatNumber=number)
                sv_status = "validated" if getattr(res, "valid", False) else "unvalidated"
            except Exception:
                sv_status = None

    if seller_vat:
        if sv_status:
            pdf.cell(0, 6, f"VAT: {seller_vat} ({sv_status})", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        else:
            pdf.cell(0, 6, f"VAT: {seller_vat}", new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    pdf.ln(4)
    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 8, "Customer", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_font("Helvetica", "", 11)
    pdf.cell(0, 6, f"{invoice.customer_name}", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.multi_cell(0, 6, f"{invoice.customer_address}")

    try:
        ctype = invoice.customer_type.value if hasattr(invoice.customer_type, "value") else str(invoice.customer_type)
    except Exception:
        ctype = str(invoice.customer_type)

    if ctype == "business" and getattr(invoice, "customer_vat_number", None):
        buyer_vat = invoice.customer_vat_number
        bv_status = None
        if hasattr(invoice, "buyer_vat_validated"):
            bv_status = "validated" if invoice.buyer_vat_validated else "unvalidated"
        else:
            try:
                from zeep import Client
                wsdl = "https://ec.europa.eu/taxation_customs/vies/checkVatService.wsdl"
                client = Client(wsdl=wsdl)
                country = buyer_vat[:2]
                number = buyer_vat[2:]
                res = client.service.checkVat(countryCode=country, vatNumber=number)
                bv_status = "validated" if getattr(res, "valid", False) else "unvalidated"
            except Exception:
                bv_status = None

        if bv_status:
            pdf.cell(0, 6, f"VAT: {buyer_vat} ({bv_status})", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        else:
            pdf.cell(0, 6, f"VAT: {buyer_vat}", new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    pdf.ln(6)
    pdf.set_font("Helvetica", "", 12)
    pdf.cell(0, 6, f"Subtotal: {invoice.subtotal}", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.cell(0, 6, f"VAT ({invoice.vat_rate}%): {invoice.vat_total}", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.cell(0, 6, f"Total: {invoice.total}", new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    pdf.ln(5)
    pdf.set_font("Helvetica", "I", 10)
    try:
        ps = invoice.payment_system.value if hasattr(invoice.payment_system, "value") else str(invoice.payment_system)
    except Exception:
        ps = str(getattr(invoice, "payment_system", "web2"))

    # Payment section header
    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 8, "Payment Method", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_font("Helvetica", "", 11)
    pdf.cell(0, 6, f"{ps.upper()}", new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    # Web3-specific display
    try:
        is_web3 = (ps == "web3" or (hasattr(invoice, "payment_system") and getattr(invoice.payment_system, "value", None) == "web3"))
        tx = getattr(invoice, "blockchain_tx_id", None)
        if is_web3:
            if tx:
                # Shorten for readability: keep prefix/suffix
                def shorten(h):
                    if not isinstance(h, str):
                        return str(h)
                    if len(h) <= 16:
                        return h
                    return h[:8] + "..." + h[-6:]

                formatted = shorten(tx)
                pdf.cell(0, 6, f"Blockchain TX ID: {formatted}", new_x=XPos.LMARGIN, new_y=YPos.NEXT)

                # Optional: QR code linking to explorer if qrcode available
                if qrcode:
                    try:
                        explorer = getattr(invoice, "explorer_url", None) or f"https://etherscan.io/tx/{tx}"
                        img = qrcode.make(explorer)
                        with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tf:
                            img.save(tf.name)
                            tmp_path = tf.name
                        try:
                            pdf.image(tmp_path, x=150, y=pdf.get_y()-10, w=40)
                        finally:
                            try:
                                os.unlink(tmp_path)
                            except Exception:
                                pass
                    except Exception:
                        pass

            # Compliance disclaimer (MiCAR)
            pdf.ln(4)
            pdf.set_font("Helvetica", "I", 9)
            disclaimer = "This transaction may be subject to MiCAR reporting requirements. Please consult your compliance officer."
            for line in textwrap.wrap(disclaimer, width=90):
                pdf.multi_cell(0, 5, line)
    except Exception:
        pass

    try:
        if (ps == "web3" or (hasattr(invoice, "payment_system") and getattr(invoice.payment_system, "value", None) == "web3")) and getattr(invoice, "blockchain_tx_id", None):
            pdf.multi_cell(0, 10, f"Blockchain / Smart Contract ID: {invoice.blockchain_tx_id}")
    except Exception:
        pass

    filename = f"invoice_{invoice.invoice_number}.pdf"
    pdf.output(filename)
    return filename

    try:
        if (ps == "web3" or (hasattr(invoice, "payment_system") and getattr(invoice.payment_system, "value", None) == "web3")) and getattr(invoice, "blockchain_tx_id", None):
            pdf.multi_cell(0, 10, f"Blockchain / Smart Contract ID: {invoice.blockchain_tx_id}")
    except Exception:
        pass

    filename = f"invoice_{invoice.invoice_number}.pdf"
    pdf.output(filename)
    return filename
