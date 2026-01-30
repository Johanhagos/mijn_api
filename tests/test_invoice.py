import os
from types import SimpleNamespace
from decimal import Decimal


def test_create_invoice_c2b():
    # use in-memory sqlite for tests
    os.environ["DATABASE_URL"] = "sqlite:///:memory:"

    from fastapi.testclient import TestClient
    from app.main import app

    client = TestClient(app)

    payload = {
        "order_number": "ORD-TEST-1",
        "invoice_date": "2026-01-30",
        "payment_date": "2026-02-13",
        "seller_name": "Test Seller",
        "seller_address": "Seller St 1",
        "seller_vat_number": "NL123",
        "customer_type": "individual",
        "customer_name": "John Consumer",
        "customer_address": "Consumer Rd 2",
        "subtotal": "200.00",
        "vat_rate": "21.00",
    }

    r = client.post("/invoice/create", json=payload)
    assert r.status_code == 200, r.text
    data = r.json()
    assert data.get("invoice_number") == 1
    assert str(Decimal(data.get("subtotal"))) == "200.00"
    # vat_total should be 42.00 for 21%
    assert str(Decimal(data.get("vat_total"))) == "42.00"
    assert str(Decimal(data.get("total"))) == "242.00"


def test_create_invoice_pdf_b2b_vies_valid(monkeypatch):
    os.environ["DATABASE_URL"] = "sqlite:///:memory:"

    # mock zeep Client used in the endpoint
    class DummyService:
        def checkVat(self, countryCode, vatNumber):
            return SimpleNamespace(valid=True)

    class DummyClient:
        def __init__(self, *args, **kwargs):
            self.service = DummyService()

    monkeypatch.setenv("DATABASE_URL", "sqlite:///:memory:")
    # patch the Client in the invoice route module
    import app.api.routes.invoice as invmod

    monkeypatch.setattr(invmod, "Client", DummyClient)

    from fastapi.testclient import TestClient
    from app.main import app

    client = TestClient(app)

    payload = {
        "order_number": "ORD-TEST-2",
        "invoice_date": "2026-01-30",
        "payment_date": "2026-02-13",
        "seller_name": "Test Seller",
        "seller_address": "Seller St 1",
        "seller_vat_number": "NL123",
        "customer_type": "business",
        "customer_name": "Acme BV",
        "customer_address": "Business Rd 5",
        "customer_vat_number": "NL123456789B01",
        "subtotal": "100.00",
        "vat_rate": "21.00",
    }

    r = client.post("/invoice/create_pdf", json=payload)
    assert r.status_code == 200, r.text
    # should be a PDF response
    assert r.headers.get("content-type", "").startswith("application/pdf")
    assert len(r.content) > 0


def test_create_invoice_pdf_b2b_vies_invalid(monkeypatch):
    os.environ["DATABASE_URL"] = "sqlite:///:memory:"

    class DummyServiceInvalid:
        def checkVat(self, countryCode, vatNumber):
            return SimpleNamespace(valid=False)

    class DummyClientInvalid:
        def __init__(self, *args, **kwargs):
            self.service = DummyServiceInvalid()

    import app.api.routes.invoice as invmod
    monkeypatch.setattr(invmod, "Client", DummyClientInvalid)

    from fastapi.testclient import TestClient
    from app.main import app

    client = TestClient(app)

    payload = {
        "order_number": "ORD-TEST-3",
        "invoice_date": "2026-01-30",
        "payment_date": "2026-02-13",
        "seller_name": "Test Seller",
        "seller_address": "Seller St 1",
        "seller_vat_number": "NL123",
        "customer_type": "business",
        "customer_name": "Acme BV",
        "customer_address": "Business Rd 5",
        "customer_vat_number": "NLINVALID",
        "subtotal": "100.00",
        "vat_rate": "21.00",
    }

    r = client.post("/invoice/create_pdf", json=payload)
    assert r.status_code == 400
