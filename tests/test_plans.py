"""Merchants get access (dashboard data, API keys, webshop checkout) only with a paid plan.
A plan is paid in APIUSD and becomes active only after the payment is verified on-chain.

The blockchain is simulated (crypto_payments.verify_transfer is replaced).
"""
import importlib
import json
import os
import sys
import time
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

WALLET = "0xaff58640036e6c343e772D6B268C00FAA9265fc1"  # platform wallet (plans)
SHOP_WALLET = "0x" + "2" * 40  # merchants' own payout wallet (shop sales)
ADMIN = {"name": "plan_admin@example.com", "password": "admin-pass-123"}
CHAIN = {}  # tx_hash -> simulated verify_transfer result
CHECKED_WALLETS = {}  # tx_hash -> wallet the payment had to go to


def _fake_verify(cfg, tx_hash, rpc=None):
    CHECKED_WALLETS[tx_hash] = cfg.wallet_address
    return dict(CHAIN.get(tx_hash, {"state": "pending", "confirmations": 0, "units": 0}))


def _pay(c, invoice_id, amount):
    tx = "0x" + uuid.uuid4().hex + uuid.uuid4().hex
    CHAIN[tx] = {"state": "confirmed", "units": int(round(amount * 1_000_000)), "payer": "0x" + "1" * 40,
                 "block_number": 1, "confirmations": 3, "timestamp": int(time.time())}
    return c.post(f"/pay/{invoice_id}/transactions", json={"tx_hash": tx})


@pytest.fixture(scope="module")
def env(tmp_path_factory):
    from passlib.context import CryptContext
    data_dir = tmp_path_factory.mktemp("data")
    (data_dir / "users.json").write_text(json.dumps([
        {"id": 7101, "name": ADMIN["name"], "password": CryptContext(schemes=["bcrypt"]).hash(ADMIN["password"]),
         "role": "admin"}]), encoding="utf-8")
    mp = pytest.MonkeyPatch()
    mp.delenv("RAILWAY_ENVIRONMENT", raising=False)
    mp.setenv("DATA_DIR", str(data_dir))
    mp.setenv("DATABASE_URL", os.getenv("TEST_DATABASE_URL") or f"sqlite:///{(data_dir / 'plans.db').as_posix()}")
    mp.setenv("PAYMENT_WALLET_ADDRESS", WALLET)
    import app.store as store
    if store._engine is not None:
        store._engine.dispose()
    store._engine, store._engine_url = None, None
    from sqlalchemy import create_engine
    eng = create_engine(os.environ["DATABASE_URL"]); store.metadata.drop_all(eng); eng.dispose()

    import main
    importlib.reload(main)
    mp.setattr(main.crypto_payments, "verify_transfer", _fake_verify)
    client = TestClient(main.app)
    yield {"main": main, "client": client, "mp": mp, "admin": _login(client, ADMIN["name"], ADMIN["password"])}
    mp.undo()


def _login(client, name, password):
    r = client.post("/login", json={"name": name, "password": password})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def _merchant(c, country="NL", wallet=SHOP_WALLET):
    name = f"m_{uuid.uuid4().hex[:6]}"
    c.post("/register", json={"name": name, "email": f"{name}@example.com", "password": "merchant-pass-1",
                              "business_name": f"{name} BV", "country": country})
    auth = _login(c, name, "merchant-pass-1")
    if wallet:
        assert c.put("/merchant/profile", headers=auth, json={"payoutWallet": wallet}).status_code == 200
    return name, auth


def _activate(env, auth, plan="professional"):
    """Buy a plan and pay its full amount (incl. VAT)."""
    buy = _buy(env, auth, plan)
    assert _pay(env["client"], buy["invoice_id"], buy["amount"]).json()["status"] == "paid"
    return buy


def _buy(env, auth, plan="professional"):
    r = env["client"].post("/plans/checkout", headers=auth, json={"plan": plan})
    assert r.status_code == 200, r.text
    return r.json()


def _invoice(c, auth):
    return c.post("/invoices", headers=auth, json={
        "seller_name": "Shop", "seller_country": "NL", "buyer_name": "Buyer", "buyer_country": "NL",
        "items": [{"description": "x", "quantity": 1, "unit_price": 10}], "vat_rate": 0})


def _set_expiry(main, name, when):
    users = main.store.load_users()
    next(u for u in users if u["name"] == name)["plan_expires_at"] = when.isoformat()
    main.store.save_users(users)


def test_no_access_without_a_plan(env):
    c = env["client"]
    _, auth = _merchant(c)
    me = c.get("/merchant/me", headers=auth).json()
    assert me["plan_active"] is False
    assert _invoice(c, auth).status_code == 402
    assert c.get("/invoices", headers=auth).status_code == 402
    assert c.post("/api-keys", headers=auth, json={"label": "x"}).status_code == 402
    assert c.get("/api-keys", headers=auth).status_code == 402


def test_plans_are_listed_with_server_prices(env):
    plans = {p["id"]: p for p in env["client"].get("/plans").json()}
    assert plans["starter"]["price"] == 20.0 and plans["professional"]["price"] == 29.99
    assert plans["enterprise"]["purchasable"] is False


def test_plan_is_active_only_after_verified_payment(env):
    c = env["client"]
    _, auth = _merchant(c)
    # The browser cannot choose the price
    buy = c.post("/plans/checkout", headers=auth, json={"plan": "professional", "price": 0.01}).json()
    assert buy["subtotal"] == 29.99 and buy["vat_rate"] == 21.0 and buy["amount"] == 36.29
    view = c.get(f"/pay/{buy['invoice_id']}").json()
    assert view["amount_due"] == "36.290000" and view["kind"] == "plan" and view["payable"]
    assert view["wallet_address"] == WALLET  # plans are paid to the platform
    assert view["return_url"].endswith("/dashboard")

    # Submitted but not yet confirmed: still no access
    tx = "0x" + "cd" * 32
    c.post(f"/pay/{buy['invoice_id']}/transactions", json={"tx_hash": tx})
    assert c.get("/merchant/me", headers=auth).json()["plan_active"] is False
    # Paid too little: still no access
    assert _pay(c, buy["invoice_id"], 10).json()["status"] == "partially_paid"
    assert c.get("/merchant/me", headers=auth).json()["plan_active"] is False
    # Paid the rest: access
    assert _pay(c, buy["invoice_id"], 26.29).json()["status"] == "paid"
    me = c.get("/merchant/me", headers=auth).json()
    assert me["plan_active"] is True and me["plan"] == "professional"
    expires = datetime.fromisoformat(me["plan_expires_at"])
    assert timedelta(days=29) < expires - datetime.now(timezone.utc) <= timedelta(days=30)
    assert _invoice(c, auth).status_code == 201
    assert c.post("/api-keys", headers=auth, json={"label": "x"}).status_code == 200


def test_checkout_reuses_the_open_plan_invoice(env):
    c = env["client"]
    _, auth = _merchant(c)
    assert _buy(env, auth)["invoice_id"] == _buy(env, auth)["invoice_id"]
    assert _buy(env, auth, "starter")["invoice_id"] != _buy(env, auth)["invoice_id"]
    for bad in ("enterprise", "free", ""):
        assert c.post("/plans/checkout", headers=auth, json={"plan": bad}).status_code == 400


def test_plan_invoice_is_not_a_merchant_invoice(env):
    c = env["client"]
    _, auth = _merchant(c)
    buy = _activate(env, auth)
    assert buy["invoice_id"] not in {i["id"] for i in c.get("/invoices", headers=auth).json()}
    assert c.patch(f"/invoices/{buy['invoice_id']}", headers=auth, json={"notes": "x"}).status_code == 404
    assert buy["invoice_id"] in {i["id"] for i in c.get("/invoices?all=true", headers=env["admin"]).json()}


def test_paying_again_extends_the_plan(env):
    c = env["client"]
    _, auth = _merchant(c)
    _activate(env, auth)
    first = datetime.fromisoformat(c.get("/merchant/me", headers=auth).json()["plan_expires_at"])
    _activate(env, auth)
    second = datetime.fromisoformat(c.get("/merchant/me", headers=auth).json()["plan_expires_at"])
    assert timedelta(days=29, hours=23) < second - first <= timedelta(days=30)


def test_expired_plan_blocks_dashboard_and_webshop(env):
    c, main = env["client"], env["main"]
    name, auth = _merchant(c)
    _activate(env, auth)
    key = c.post("/api-keys", headers=auth, json={"label": "shop"}).json()["key"]
    assert c.post("/create_session", headers={"x-api-key": key}, json={"amount": 5}).status_code == 200

    _set_expiry(main, name, datetime.now(timezone.utc) - timedelta(minutes=1))
    assert c.get("/merchant/me", headers=auth).json()["plan_active"] is False
    assert c.get("/invoices", headers=auth).status_code == 402
    assert c.post("/create_session", headers={"x-api-key": key}, json={"amount": 5}).status_code == 402
    assert c.post("/checkout", headers={"x-api-key": key}, json={"amount": 5}).status_code == 402


def test_invalid_api_key_is_rejected(env):
    c = env["client"]
    assert c.post("/create_session", headers={"x-api-key": "sk_live_nope"}, json={"amount": 5}).status_code == 403
    assert c.post("/create_session", json={"amount": 5}).status_code == 401


def test_starter_monthly_limit(env):
    c, main, mp = env["client"], env["main"], env["mp"]
    mp.setitem(main.PLANS["starter"], "monthly_invoices", 2)
    _, auth = _merchant(c)
    _activate(env, auth, "starter")
    key = c.post("/api-keys", headers=auth, json={"label": "shop"}).json()["key"]
    assert _invoice(c, auth).status_code == 201
    assert c.post("/create_session", headers={"x-api-key": key}, json={"amount": 5}).status_code == 200
    assert _invoice(c, auth).status_code == 402
    assert c.post("/create_session", headers={"x-api-key": key}, json={"amount": 5}).status_code == 402
    mp.setitem(main.PLANS["starter"], "monthly_invoices", 100)


def test_admin_can_grant_and_remove_a_plan(env):
    c, main = env["client"], env["main"]
    name, auth = _merchant(c)
    uid = next(u["id"] for u in main.store.load_users() if u["name"] == name)
    assert c.post(f"/admin/users/{uid}/plan", headers=auth, json={"plan": "enterprise"}).status_code == 403
    r = c.post(f"/admin/users/{uid}/plan", headers=env["admin"], json={"plan": "enterprise", "days": 365})
    assert r.status_code == 200 and r.json()["plan_active"] is True
    assert _invoice(c, auth).status_code == 201
    c.post(f"/admin/users/{uid}/plan", headers=env["admin"], json={"plan": None})
    assert _invoice(c, auth).status_code == 402


def test_api_keys_are_stored_hashed(env):
    c, main = env["client"], env["main"]
    _, auth = _merchant(c)
    _activate(env, auth)
    raw = c.post("/api-keys", headers=auth, json={"label": "shop", "mode": "live"}).json()["key"]
    stored = json.dumps(main.store.load_api_keys())
    assert raw not in stored
    listed = c.get("/api-keys", headers=auth).json()
    assert listed[0]["key_masked"] == f"sk_live_****{raw[-4:]}"
    # The hashed key works for the webshop and for the API
    assert c.post("/create_session", headers={"x-api-key": raw}, json={"amount": 5}).status_code == 200
    assert c.get("/invoices", headers={"X-API-Key": raw}).status_code == 200


def test_checkout_invoice_has_seller_buyer_and_lines(env):
    c = env["client"]
    name, auth = _merchant(c)
    _activate(env, auth)
    key = c.post("/api-keys", headers=auth, json={"label": "shop"}).json()["key"]
    s = c.post("/create_session", headers={"x-api-key": key}, json={
        "amount": 12.5, "order_id": "1042", "customer_name": "Jane", "customer_email": "jane@example.com",
        "buyer_country": "DE", "success_url": "https://shop.example/thanks?order=1042",
        "items": [{"name": "T-shirt", "quantity": 2, "unit_price": 5}, {"name": "Shipping", "quantity": 1, "unit_price": 2.5}],
    }).json()
    assert s["url"].startswith("https://apiblockchain-production-production.up.railway.app/checkout?session=")
    inv_id = c.post(f"/session/{s['id']}/pay-crypto").json()["invoice_id"]
    inv = c.get(f"/invoices/{inv_id}", headers=auth).json()
    assert inv["seller_name"] == f"{name} BV" and inv["buyer_name"] == "Jane" and inv["buyer_country"] == "DE"
    assert inv["order_number"] == "1042"
    assert [i["description"] for i in inv["items"]] == ["T-shirt", "Shipping"] and inv["total"] == 12.5
    assert _pay(c, inv_id, 12.5).json()["return_url"] == "https://shop.example/thanks?order=1042"


def test_shop_sales_are_paid_to_the_merchants_own_wallet(env):
    c = env["client"]
    _, auth = _merchant(c, wallet="0x" + "3" * 40)
    _activate(env, auth)
    key = c.post("/api-keys", headers=auth, json={"label": "shop"}).json()["key"]
    sid = c.post("/create_session", headers={"x-api-key": key}, json={"amount": 5}).json()["id"]
    inv_id = c.post(f"/session/{sid}/pay-crypto").json()["invoice_id"]
    assert c.get(f"/pay/{inv_id}").json()["wallet_address"] == "0x" + "3" * 40
    r = _pay(c, inv_id, 5)
    assert r.json()["status"] == "paid"
    tx = r.json()["payments"][0]["tx_hash"]
    assert CHECKED_WALLETS[tx] == "0x" + "3" * 40  # verified against the merchant wallet, not the platform's
    # A dashboard crypto invoice goes to the merchant wallet as well
    inv = c.post("/invoices", headers=auth, json={
        "seller_name": "Shop", "buyer_name": "B", "items": [{"description": "x", "quantity": 1, "unit_price": 3}],
        "vat_rate": 0, "payment_system": "web3"}).json()
    assert c.get(f"/pay/{inv['id']}").json()["wallet_address"] == "0x" + "3" * 40


def test_no_crypto_sales_without_a_payout_wallet(env):
    c = env["client"]
    _, auth = _merchant(c, wallet=None)
    _activate(env, auth)
    key = c.post("/api-keys", headers=auth, json={"label": "shop"}).json()["key"]
    assert c.post("/create_session", headers={"x-api-key": key}, json={"amount": 5}).status_code == 409
    r = c.post("/invoices", headers=auth, json={
        "seller_name": "Shop", "buyer_name": "B", "items": [{"description": "x", "quantity": 1, "unit_price": 3}],
        "payment_system": "web3"})
    assert r.status_code == 400
    assert c.put("/merchant/profile", headers=auth, json={"payoutWallet": "not-a-wallet"}).status_code == 400


def test_plan_vat_by_country(env):
    c, main, mp = env["client"], env["main"], env["mp"]
    vies = {}
    mp.setattr(main, "_vies_valid", lambda number: vies.get(number))

    def quote(country, vat_number=None):
        _, auth = _merchant(c, country=country)
        if vat_number:
            c.put("/merchant/profile", headers=auth, json={"vatNumber": vat_number})
        return _buy(env, auth)

    nl = quote("NL")  # platform country: domestic VAT
    assert (nl["vat_rate"], nl["vat_amount"], nl["amount"]) == (21.0, 6.30, 36.29)
    de = quote("DE")  # other EU country: its own VAT through OSS
    assert (de["vat_rate"], de["amount"]) == (19.0, 35.69) and "One-Stop-Shop" in de["vat_note"]
    assert quote("FR")["vat_rate"] == 20.0 and quote("EE")["vat_rate"] == 24.0
    vies["DE123456789"] = True  # EU business with a verified VAT number: reverse charge
    rc = quote("DE", "DE123456789")
    assert (rc["vat_rate"], rc["amount"]) == (0.0, 29.99) and "reverse charge" in rc["vat_note"]
    assert quote("DE", "DE999999999")["vat_rate"] == 19.0  # VIES says no: VAT charged
    assert quote("NL", "NL123456789B01")["vat_rate"] == 21.0  # same country: always VAT
    us = quote("US")  # outside the EU: 0%
    assert (us["vat_rate"], us["amount"]) == (0.0, 29.99)
    assert quote("CH")["vat_rate"] == 0.0


def test_plan_needs_a_country_and_follows_country_changes(env):
    c, main = env["client"], env["main"]
    name, auth = _merchant(c, country="DE")
    first = _buy(env, auth)
    assert c.put("/merchant/profile", headers=auth, json={"country": "Germany"}).status_code == 400
    c.put("/merchant/profile", headers=auth, json={"country": "be"})
    second = _buy(env, auth)
    assert second["invoice_id"] != first["invoice_id"] and second["vat_rate"] == 21.0
    users = main.store.load_users()
    next(u for u in users if u["name"] == name)["country"] = None
    main.store.save_users(users)
    assert c.post("/plans/checkout", headers=auth, json={"plan": "starter"}).status_code == 400


def test_quote_shows_prices_with_vat(env):
    c = env["client"]
    _, auth = _merchant(c, country="DE")
    q = c.get("/plans/quote", headers=auth).json()
    prices = {p["id"]: p for p in q["plans"]}
    assert q["country"] == "DE" and prices["starter"]["total"] == 23.80 and prices["professional"]["vat_rate"] == 19.0
