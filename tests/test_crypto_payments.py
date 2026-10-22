"""Invoice payments in APIUSD: paid only after on-chain confirmation, underpayment is
partially paid, each transaction counts once, and nobody but an admin can mark paid.

The blockchain is simulated (crypto_payments.verify_transfer is replaced); set
RUN_CHAIN_TESTS=1 to also check a real Sepolia transaction.
"""
import hashlib
import hmac
import importlib
import json
import os
import sys
import time
import uuid
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

WALLET = "0xaff58640036e6c343e772D6B268C00FAA9265fc1"
ADMIN = {"name": "pay_admin@example.com", "password": "admin-pass-123"}
CHAIN = {}  # tx_hash -> simulated verify_transfer result


def _tx():
    return "0x" + uuid.uuid4().hex + uuid.uuid4().hex


def _fake_verify(cfg, tx_hash, rpc=None):
    return dict(CHAIN.get(tx_hash, {"state": "pending", "confirmations": 0, "units": 0}))


def _confirmed(units, ts=None, confirmations=3):
    return {"state": "confirmed", "units": units, "payer": "0x" + "1" * 40, "block_number": 1,
            "confirmations": confirmations, "timestamp": ts or int(time.time())}


@pytest.fixture(scope="module")
def env(tmp_path_factory):
    from passlib.context import CryptContext
    data_dir = tmp_path_factory.mktemp("data")
    (data_dir / "users.json").write_text(json.dumps([
        {"id": 7001, "name": ADMIN["name"], "password": CryptContext(schemes=["bcrypt"]).hash(ADMIN["password"]),
         "role": "admin"}]), encoding="utf-8")
    mp = pytest.MonkeyPatch()
    mp.delenv("RAILWAY_ENVIRONMENT", raising=False)
    mp.setenv("DATA_DIR", str(data_dir))
    mp.setenv("DATABASE_URL", os.getenv("TEST_DATABASE_URL") or f"sqlite:///{(data_dir / 'pay.db').as_posix()}")
    mp.setenv("PAYMENT_WALLET_ADDRESS", WALLET)
    mp.delenv("STRIPE_WEBHOOK_SECRET", raising=False)
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

    admin = _login(client, ADMIN["name"], ADMIN["password"])
    name = f"merchant_{uuid.uuid4().hex[:6]}"
    client.post("/register", json={"name": name, "email": f"{name}@example.com", "password": "merchant-pass-1"})
    merchant = _login(client, name, "merchant-pass-1")
    yield {"main": main, "client": client, "admin": admin, "merchant": merchant, "mp": mp}
    mp.undo()


def _login(client, name, password):
    r = client.post("/login", json={"name": name, "password": password})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def _invoice(env, total=10.0, payment_system="web3"):
    r = env["client"].post("/invoices", headers=env["merchant"], json={
        "seller_name": "Shop", "seller_country": "NL", "buyer_name": "Buyer", "buyer_country": "NL",
        "items": [{"description": "x", "quantity": 1, "unit_price": total}], "vat_rate": 0, "total": total,
        "payment_system": payment_system})
    assert r.status_code == 201, r.text
    return r.json()["id"]


def _submit(env, inv_id, tx):
    return env["client"].post(f"/pay/{inv_id}/transactions", json={"tx_hash": tx})


def test_payment_page_shows_amount_and_wallet(env):
    inv = _invoice(env, 12.5)
    view = env["client"].get(f"/pay/{inv}").json()
    assert view["amount_due"] == "12.500000"
    assert view["wallet_address"] == WALLET
    assert view["token"]["symbol"] == "APIUSD" and view["chain"]["id"] == 11155111
    assert view["payable"] is True and view["status"] == "issued"


def test_full_payment_marks_paid_only_when_confirmed(env):
    inv = _invoice(env, 10)
    tx = _tx()
    CHAIN[tx] = {"state": "pending", "confirmations": 1, "units": 10_000_000}
    r = _submit(env, inv, tx)
    assert r.status_code == 200 and r.json()["status"] == "issued"
    assert tx in r.json()["pending_txs"]

    CHAIN[tx] = _confirmed(10_000_000)
    view = env["client"].get(f"/pay/{inv}").json()  # page polling re-checks pending txs
    assert view["status"] == "paid" and view["amount_paid"] == "10.000000"
    detail = env["client"].get(f"/invoices/{inv}", headers=env["merchant"]).json()
    assert detail["status"] == "paid" and detail["amount_paid"] == 10.0


def test_underpayment_is_partially_paid_then_paid(env):
    inv = _invoice(env, 10)
    tx1, tx2 = _tx(), _tx()
    CHAIN[tx1] = _confirmed(4_000_000)
    v = _submit(env, inv, tx1).json()
    assert v["status"] == "partially_paid" and v["amount_remaining"] == "6.000000"
    CHAIN[tx2] = _confirmed(6_000_000)
    assert _submit(env, inv, tx2).json()["status"] == "paid"


def test_overpayment_is_overpaid(env):
    inv = _invoice(env, 50)
    tx = _tx()
    CHAIN[tx] = _confirmed(60_000_000)
    v = _submit(env, inv, tx).json()
    assert v["status"] == "overpaid" and v["amount_paid"] == "60.000000"
    assert v["amount_remaining"] == "0.000000" and v["payable"] is False
    detail = env["client"].get(f"/invoices/{inv}", headers=env["merchant"]).json()
    assert detail["status"] == "overpaid" and detail["payment_symbol"] == "APIUSD"
    assert detail["payments"] == [{"tx_hash": tx, "amount": "60.000000",
                                   "explorer_url": f"https://sepolia.etherscan.io/tx/{tx}"}]


def test_paid_then_extra_payment_is_overpaid(env):
    inv = _invoice(env, 10)
    tx1, tx2 = _tx(), _tx()
    CHAIN[tx1], CHAIN[tx2] = _confirmed(10_000_000), _confirmed(1_000_000)
    assert _submit(env, inv, tx1).json()["status"] == "paid"
    assert _submit(env, inv, tx2).json()["status"] == "overpaid"


def test_reverted_transaction_reports_failed(env):
    inv = _invoice(env, 10)
    tx = _tx()
    CHAIN[tx] = {"state": "failed", "reason": "Transaction failed on the blockchain"}
    r = _submit(env, inv, tx)
    assert r.status_code == 400 and r.json()["results"][0]["state"] == "failed"
    assert r.json()["status"] == "issued"


def test_web2_invoice_is_not_paid_in_crypto(env):
    inv = _invoice(env, 10, payment_system="web2")
    view = env["client"].get(f"/pay/{inv}").json()
    assert view["payable"] is False and view["payment_system"] == "web2"
    tx = _tx()
    CHAIN[tx] = _confirmed(10_000_000)
    assert _submit(env, inv, tx).status_code == 409
    assert env["client"].get(f"/pay/{inv}").json()["status"] == "issued"


def test_same_transaction_counts_once(env):
    inv, other = _invoice(env, 10), _invoice(env, 10)
    tx = _tx()
    CHAIN[tx] = _confirmed(5_000_000)
    _submit(env, inv, tx)
    again = _submit(env, inv, tx).json()
    assert again["amount_paid"] == "5.000000" and again["status"] == "partially_paid"
    reused = _submit(env, other, tx)
    assert reused.status_code == 400
    assert env["client"].get(f"/pay/{other}").json()["amount_paid"] == "0.000000"


def test_rejected_transactions_change_nothing(env):
    inv = _invoice(env, 10)
    wrong_wallet, reverted, too_old = _tx(), _tx(), _tx()
    CHAIN[wrong_wallet] = {"state": "invalid", "reason": "no transfer to the payment address"}
    CHAIN[reverted] = {"state": "failed", "reason": "failed"}
    CHAIN[too_old] = _confirmed(10_000_000, ts=int(time.time()) - 86400)
    for tx in (wrong_wallet, reverted, too_old):
        assert _submit(env, inv, tx).status_code == 400
    assert env["client"].get(f"/pay/{inv}").json()["status"] == "issued"
    assert _submit(env, inv, "not-a-hash").status_code == 400


def test_only_admin_can_mark_paid(env):
    c = env["client"]
    inv = _invoice(env, 10)
    assert c.patch(f"/invoices/{inv}", headers=env["merchant"], json={"status": "paid"}).status_code == 403
    r = c.post("/invoices", headers=env["merchant"], json={
        "seller_name": "S", "buyer_name": "B", "items": [{"description": "x", "quantity": 1, "unit_price": 1}],
        "status": "paid"})
    assert r.status_code == 403
    assert c.patch(f"/invoices/{inv}", headers=env["admin"], json={"status": "paid"}).status_code == 200
    # ...and a merchant cannot undo it either
    assert c.patch(f"/invoices/{inv}", headers=env["merchant"], json={"status": "overdue"}).status_code == 403


def test_no_unverified_paths_to_paid(env):
    c, main = env["client"], env["main"]
    for hook in ("/webhooks/paypal", "/webhooks/onecom", "/webhooks/web3"):
        assert c.post(hook, json={"event": "payment.confirmed", "session_id": "x"}).status_code == 410
    assert c.post("/webhooks/stripe", json={"type": "payment_intent.succeeded"}).status_code == 503
    assert c.post("/session/whatever/complete", json={"payment_system": "web3"},
                  headers=env["merchant"]).status_code == 403
    r = c.post("/checkout", headers={"X-API-Key": "dev"}, json={"amount": 5, "mode": "test"})
    assert r.json()["invoice"]["status"] == "pending"


def test_stripe_webhook_requires_valid_signature(env):
    c, mp = env["client"], env["mp"]
    mp.setenv("STRIPE_WEBHOOK_SECRET", "whsec_test")
    body = json.dumps({"type": "payment_intent.succeeded", "data": {"object": {"id": "pi_x", "metadata": {}}}})
    assert c.post("/webhooks/stripe", content=body, headers={"Stripe-Signature": "t=1,v1=bad"}).status_code == 401
    ts = str(int(time.time()))
    sig = hmac.new(b"whsec_test", f"{ts}.{body}".encode(), hashlib.sha256).hexdigest()
    ok = c.post("/webhooks/stripe", content=body, headers={"Stripe-Signature": f"t={ts},v1={sig}"})
    assert ok.status_code != 401  # signature accepted (400: no session id in this event)
    mp.delenv("STRIPE_WEBHOOK_SECRET")


def test_hosted_checkout_pays_through_invoice(env):
    main, c = env["main"], env["client"]
    sessions = main.store.load_sessions()
    sid = f"sess_{uuid.uuid4().hex[:8]}"
    sessions.append({"id": sid, "merchant_id": 1, "amount": 7.0, "mode": "live", "status": "created",
                     "metadata": {"webhook_sources": []}})
    main.store.save_sessions(sessions)
    first = c.post(f"/session/{sid}/pay-crypto").json()
    assert c.post(f"/session/{sid}/pay-crypto").json()["invoice_id"] == first["invoice_id"]  # created once
    assert first["payment_url"].endswith(f"/pay?invoice={first['invoice_id']}")
    tx = _tx()
    CHAIN[tx] = _confirmed(7_000_000)
    assert _submit(env, first["invoice_id"], tx).json()["status"] == "paid"
    assert next(s for s in main.store.load_sessions() if s["id"] == sid)["status"] == "paid"


@pytest.mark.skipif(os.getenv("RUN_CHAIN_TESTS") != "1", reason="needs Sepolia RPC access")
def test_real_sepolia_transfer(monkeypatch):
    from app import crypto_payments as cp
    monkeypatch.setenv("PAYMENT_WALLET_ADDRESS", "0xbae6217303a25FAd7cFBa62b9209321cd1B63CC2")
    tx = "0x9bf8344f421b99ae3021d4f36c910df891f7bf836fec6bbc320d930fe61a2acf"
    r = importlib.reload(cp).verify_transfer(cp.config(), tx)
    assert r["state"] == "confirmed" and r["units"] == 1_000_000
    monkeypatch.setenv("PAYMENT_WALLET_ADDRESS", WALLET)
    assert cp.verify_transfer(cp.config(), tx)["state"] == "invalid"


def test_unknown_transaction_expires(env):
    main = env["main"]
    inv = _invoice(env, 10)
    tx = _tx()  # never appears on-chain
    assert tx in _submit(env, inv, tx).json()["pending_txs"]
    invoices = main.store.load_invoices()
    doc = next(i for i in invoices if i["id"] == inv)
    doc["pending_since"][tx] -= main.PENDING_TX_TIMEOUT + 1
    main.store.save_invoices(invoices)
    view = env["client"].get(f"/pay/{inv}").json()
    assert tx not in view["pending_txs"] and view["results"][0]["state"] == "rejected"
