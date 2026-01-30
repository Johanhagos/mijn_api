from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP
try:
    from sqlalchemy.orm import Session
    from models import Shop, Customer, Invoice, InvoiceItem, Product
except Exception:
    # Allow importing this module in environments without SQLAlchemy or DB models
    Session = None
    Shop = None
    Customer = None
    Invoice = None
    InvoiceItem = None
    Product = None

# Helper for decimal rounding
def q(amount):
    return Decimal(amount).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


# Simple sequential invoice number generator (DB-backed)
def next_invoice_number(session: Session, shop: Shop) -> str:
    # This uses the current year + an incrementing sequence per shop.
    # For production use a DB sequence or a dedicated table with row-level locking.
    year = date.today().year
    prefix = shop.invoice_prefix
    stmt = (
        session.query(Invoice)
        .filter(Invoice.shop_id == shop.id, Invoice.invoice_number.like(f"{prefix}-{year}-%"))
        .order_by(Invoice.created_at.desc())
    )
    last = stmt.first()
    if not last:
        seq = 1
    else:
        try:
            seq = int(last.invoice_number.rsplit("-", 1)[-1]) + 1
        except Exception:
            seq = 1
    return f"{prefix}-{year}-{seq:06d}"


# VAT rules simplified per the table in the spec
def compute_vat_for_line(shop: Shop, customer: Customer, unit_price: Decimal, qty: int, vat_rate: Decimal):
    line = q(unit_price) * qty
    # Determine VAT applicability
    shop_country = shop.country.upper()
    cust_country = customer.country.upper()
    is_b2b = bool(customer.vat_number)

    if cust_country == shop_country:
        # Same country: charge VAT normally
        vat = q(line * vat_rate / Decimal("100"))
    else:
        # Different country
        # EU handling simplified: assume shop_country and cust_country are EU if 2-letter and not 'US'
        eu_countries = set()  # Placeholder: in prod provide real EU set or use library
        # crude EU membership check — treat non-empty and length==2 as EU for now
        is_eu_shop = len(shop_country) == 2
        is_eu_cust = len(cust_country) == 2

        if is_eu_shop and is_eu_cust:
            if is_b2b:
                # Reverse charge: 0% VAT
                vat = Decimal("0.00")
            else:
                # B2C: charge shop VAT
                vat = q(line * vat_rate / Decimal("100"))
        else:
            # Non-EU customer: 0%
            vat = Decimal("0.00")

    return q(vat)


def create_invoice(session: Session, shop_id: str, customer_id: str, items: list, actor: str = None) -> Invoice:
    shop = session.get(Shop, shop_id)
    customer = session.get(Customer, customer_id)
    assert shop is not None and customer is not None

    number = next_invoice_number(session, shop)

    subtotal = Decimal("0.00")
    vat_total = Decimal("0.00")

    invoice = Invoice(
        shop_id=shop.id,
        customer_id=customer.id,
        invoice_number=number,
        status="DRAFT",
        issue_date=date.today(),
        due_date=date.today() + timedelta(days=14),
        subtotal=Decimal("0.00"),
        vat_total=Decimal("0.00"),
        total=Decimal("0.00"),
        currency=shop.currency,
    )
    session.add(invoice)
    session.flush()  # assign invoice.id

    for it in items:
        # item: {product_id?|product_name, qty, unit_price, vat_rate}
        qty = int(it.get("qty") or it.get("quantity"))
        unit_price = Decimal(str(it.get("unit_price") or it.get("price")))
        vat_rate = Decimal(str(it.get("vat_rate")))
        product_name = it.get("product_name") or ""

        line_total = q(unit_price) * qty
        line_vat = compute_vat_for_line(shop, customer, unit_price, qty, vat_rate)

        subtotal += line_total
        vat_total += line_vat

        item_row = InvoiceItem(
            invoice_id=invoice.id,
            product_name=product_name,
            quantity=qty,
            unit_price=q(unit_price),
            vat_rate=vat_rate,
            total=q(line_total + line_vat),
        )
        session.add(item_row)

    invoice.subtotal = q(subtotal)
    invoice.vat_total = q(vat_total)
    invoice.total = q(subtotal + vat_total)

    session.commit()

    return invoice


def create_credit_note(session: Session, original_invoice_id: str, actor: str = None) -> Invoice:
    orig = session.get(Invoice, original_invoice_id)
    assert orig is not None

    if orig.status not in ("SENT", "PAID", "OVERDUE"):
        raise ValueError("Can only create credit note for SENT/PAID/OVERDUE invoices")

    shop = session.get(Shop, orig.shop_id)
    number = next_invoice_number(session, shop)

    credit = Invoice(
        shop_id=orig.shop_id,
        customer_id=orig.customer_id,
        invoice_number=number,
        status="CREDIT_NOTE",
        issue_date=date.today(),
        due_date=date.today(),
        subtotal=-orig.subtotal,
        vat_total=-orig.vat_total,
        total=-orig.total,
        currency=orig.currency,
        pdf_url=None,
    )
    session.add(credit)
    session.flush()

    for orig_item in orig.items:
        ci = InvoiceItem(
            invoice_id=credit.id,
            product_name=orig_item.product_name,
            quantity=-orig_item.quantity,
            unit_price=orig_item.unit_price,
            vat_rate=orig_item.vat_rate,
            total=-orig_item.total,
        )
        session.add(ci)

    session.commit()
    return credit


def calculate_vat(payload: dict) -> dict:
    """Lightweight VAT calculator for use by external HTTP endpoints.

    Expects payload with optional `shop` and `customer` dicts and an `items` list
    where each item contains `qty` (or `quantity`), `unit_price` (or `price`) and `vat_rate`.
    Returns dict with stringified decimal totals: subtotal, vat_total, total.
    """
    # Accept either `items` (preferred) or `lines` (legacy clients)
    items = payload.get("items") or payload.get("lines") or []

    subtotal = Decimal("0.00")
    vat_total = Decimal("0.00")

    for it in items:
        qty = int(it.get("qty") or it.get("quantity") or 1)
        unit_price = Decimal(str(it.get("unit_price") or it.get("price") or "0"))
        vat_rate = Decimal(str(it.get("vat_rate") or "0"))

        line = q(unit_price) * qty

        try:
            # Best-effort: attempt to use `compute_vat_for_line` when shop/customer
            # objects are available and compatible. Accept dicts by coercing
            # them into simple objects exposing the expected attributes.
            shop = payload.get("shop")
            customer = payload.get("customer")

            class _Simple:
                def __init__(self, d: dict | None):
                    if not d:
                        self.country = ""
                        self.vat_number = ""
                    else:
                        self.country = d.get("country", "")
                        # support both vat_number and vatNo keys
                        self.vat_number = d.get("vat_number") or d.get("vatNo") or ""

            if isinstance(shop, dict):
                shop = _Simple(shop)
            if isinstance(customer, dict):
                customer = _Simple(customer)

            v = compute_vat_for_line(shop, customer, unit_price, qty, vat_rate)
            v = Decimal(str(v))
        except Exception:
            v = q(line * vat_rate / Decimal("100"))

        subtotal += line
        vat_total += v

    total = q(subtotal + vat_total)
    return {"subtotal": str(q(subtotal)), "vat_total": str(q(vat_total)), "total": str(total)}
