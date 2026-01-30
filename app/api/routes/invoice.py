from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from decimal import Decimal
from app.schemas.invoice import InvoiceCreate, InvoiceOut, CustomerType, PaymentSystem
from app.models.invoice import Invoice, CustomerType as ModelCustomerType, PaymentSystem as ModelPaymentSystem
from app.db.session import get_db
from app.utils.pdf import generate_invoice_pdf
from zeep import Client
from zeep.exceptions import Fault

router = APIRouter(prefix="/invoice", tags=["Invoice"])

@router.post("/create", response_model=InvoiceOut)
def create_invoice(invoice_in: InvoiceCreate, db: Session = Depends(get_db)):
    # Auto-incrementing invoice number
    last_invoice = db.query(Invoice).order_by(Invoice.invoice_number.desc()).first()
    invoice_number = 1 if not last_invoice else (last_invoice.invoice_number or 0) + 1

    # Enforce B2B VAT number presence
    if invoice_in.customer_type == CustomerType.business and not invoice_in.customer_vat_number:
        raise HTTPException(status_code=400, detail="customer_vat_number is required for business customers")

    vat_total = (invoice_in.subtotal * invoice_in.vat_rate) / Decimal("100")
    total = invoice_in.subtotal + vat_total

    invoice = Invoice(
        invoice_number=invoice_number,
        order_number=invoice_in.order_number,
        invoice_date=invoice_in.invoice_date,
        payment_date=invoice_in.payment_date,
        seller_name=invoice_in.seller_name,
        seller_address=invoice_in.seller_address,
        seller_vat_number=invoice_in.seller_vat_number,
        customer_type=ModelCustomerType(invoice_in.customer_type.value if hasattr(invoice_in.customer_type, 'value') else str(invoice_in.customer_type)),
        customer_name=invoice_in.customer_name,
        customer_address=invoice_in.customer_address,
        customer_vat_number=invoice_in.customer_vat_number,
        subtotal=invoice_in.subtotal,
        vat_rate=invoice_in.vat_rate,
        vat_total=vat_total,
        total=total
    )

    # set payment system and blockchain tx id if provided
    try:
        invoice.payment_system = ModelPaymentSystem(invoice_in.payment_system.value if hasattr(invoice_in.payment_system, 'value') else str(invoice_in.payment_system))
    except Exception:
        invoice.payment_system = ModelPaymentSystem.web2
    invoice.blockchain_tx_id = invoice_in.blockchain_tx_id

    db.add(invoice)
    db.commit()
    db.refresh(invoice)
    return invoice


@router.post("/create_pdf")
def create_invoice_pdf(invoice_in: InvoiceCreate, db: Session = Depends(get_db)):
    # reuse create_invoice logic but return PDF file
    # validate B2B VAT number
    if invoice_in.customer_type == CustomerType.business and not invoice_in.customer_vat_number:
        raise HTTPException(status_code=400, detail="customer_vat_number is required for business customers")
    # If EU B2B, validate via VIES
    try:
        if invoice_in.customer_type == CustomerType.business and invoice_in.customer_vat_number:
            # expect VAT in format 'NL123456789' or with space - normalize
            v = invoice_in.customer_vat_number.replace(' ', '').upper()
            if len(v) >= 3:
                country_code = v[:2]
                vat_nr = v[2:]
                # Only attempt VIES for EU country codes (simple check: 2 letters)
                if country_code.isalpha():
                    try:
                        client = Client('https://ec.europa.eu/taxation_customs/vies/checkVatService.wsdl')
                        res = client.service.checkVat(countryCode=country_code, vatNumber=vat_nr)
                        if not getattr(res, 'valid', False):
                            raise HTTPException(status_code=400, detail="Ongeldig EU VAT-nummer")
                    except Fault:
                        raise HTTPException(status_code=400, detail="VIES check failed")
                    except Exception:
                        # If network/VIES unreachable, prefer to fail closed for safety
                        raise HTTPException(status_code=400, detail="Unable to validate VAT number via VIES")
    except HTTPException:
        raise
    except Exception:
        # any unexpected error, return generic failure
        raise HTTPException(status_code=400, detail="VAT validation error")

    # Crypto-only check: require blockchain_tx_id for web3 payments
    if invoice_in.payment_system == PaymentSystem.web3 and not invoice_in.blockchain_tx_id:
        raise HTTPException(status_code=400, detail="Blockchain TX ID vereist voor Web3 betalingen")

    # create invoice record
    last_invoice = db.query(Invoice).order_by(Invoice.invoice_number.desc()).first()
    invoice_number = 1 if not last_invoice else (last_invoice.invoice_number or 0) + 1

    vat_total = (invoice_in.subtotal * invoice_in.vat_rate) / Decimal("100")
    total = invoice_in.subtotal + vat_total

    invoice = Invoice(
        invoice_number=invoice_number,
        order_number=invoice_in.order_number,
        invoice_date=invoice_in.invoice_date,
        payment_date=invoice_in.payment_date,
        seller_name=invoice_in.seller_name,
        seller_address=invoice_in.seller_address,
        seller_vat_number=invoice_in.seller_vat_number,
        customer_type=ModelCustomerType(invoice_in.customer_type.value if hasattr(invoice_in.customer_type, 'value') else str(invoice_in.customer_type)),
        customer_name=invoice_in.customer_name,
        customer_address=invoice_in.customer_address,
        customer_vat_number=invoice_in.customer_vat_number,
        subtotal=invoice_in.subtotal,
        vat_rate=invoice_in.vat_rate,
        vat_total=vat_total,
        total=total
    )

    try:
        invoice.payment_system = ModelPaymentSystem(invoice_in.payment_system.value if hasattr(invoice_in.payment_system, 'value') else str(invoice_in.payment_system))
    except Exception:
        invoice.payment_system = ModelPaymentSystem.web2
    invoice.blockchain_tx_id = invoice_in.blockchain_tx_id

    db.add(invoice)
    db.commit()
    db.refresh(invoice)

    pdf_file = generate_invoice_pdf(invoice)
    return FileResponse(pdf_file, media_type="application/pdf", filename=pdf_file)
