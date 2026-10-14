"""Invoices and payments are stored in the database, old JSON data is imported once,
and the same payment is never counted twice.

Runs against SQLite by default. Set TEST_DATABASE_URL to run against PostgreSQL.
"""
import importlib
import json
import os
import sys
import uuid
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

OLD_INVOICES = [
    {"id": "old-inv-stripe", "merchant_id": 1, "amount": 20.0, "mode": "live", "status": "paid",
     "payment_system": "web2", "stripe_intent_id": "pi_old_1", "created_at": "2026-01-10T10:00:00"},
    {"id": "old-inv-web3", "merchant_id": 1, "amount": 5.0, "mode": "live", "status": "paid",
     "payment_system": "web3", "blockchain_tx_id": "0xABCDEF0001", "created_at": "2026-01-11T10:00:00"},
    {"id": "old-inv-rich", "invoice_number": "INV-2026-0001", "seller_name": "Seller BV", "buyer_name": "Buyer",
     "items": [{"description": "Work", "quantity": 2, "unit_price": 10, "amount": 20}],
     "subtotal": 20, "vat_rate": 21, "vat_amount": 4.2, "total": 24.2, "status": "issued",
     "created_at": "2026-01-12T10:00:00"},
]
OLD_SESSIONS = [
    {"id": f"sess_{name}", "merchant_id": 1, "amount": 10.0, "mode": "live", "status": "created",
     "success_url": "", "cancel_url": "", "url": "", "created_at": "2026-01-01T00:00:00",
     "metadata": {"webhook_sources": []}}
    for name in ("a", "b", "c", "d")
]


@pytest.fixture(scope="module")
def env(tmp_path_factory):
    data_dir = tmp_path_factory.mktemp("data")
    (data_dir / "invoices.json").write_text(json.dumps(OLD_INVOICES), encoding="utf-8")
    (data_dir / "sessions.json").write_text(json.dumps(OLD_SESSIONS), encoding="utf-8")

    mp = pytest.MonkeyPatch()
    mp.setenv("DATA_DIR", str(data_dir))
    db_url = os.getenv("TEST_DATABASE_URL") or f"sqlite:///{(data_dir / 'test.db').as_posix()}"
    mp.setenv("DATABASE_URL", db_url)
    mp.delenv("RAILWAY_ENVIRONMENT", raising=False)

    import main
    importlib.reload(main)
    yield main, TestClient(main.app), data_dir
    mp.undo()


def _stripe_event(session_id, intent_id):
    return {"type": "payment_intent.succeeded",
            "data": {"object": {"id": intent_id, "amount": 1000, "metadata": {"session_id": session_id}}}}


def _web3_event(session_id, tx):
    return {"event": "payment.confirmed", "session_id": session_id, "blockchain_tx_id": tx,
            "network": "sepolia", "amount": 10.0}


def test_old_invoices_are_imported_and_listed(env):
    main, client, _ = env
    ids = {i["id"] for i in client.get("/invoices").json()}
    assert {"old-inv-stripe", "old-inv-web3", "old-inv-rich"} <= ids
    rich = client.get("/invoices/old-inv-rich").json()
    assert rich["invoice_number"] == "INV-2026-0001"
    assert float(rich["total"]) == 24.2


def test_import_runs_only_once(env):
    main, _, data_dir = env
    before = len(main.store.load_invoices())
    main.store._import_json_once([data_dir, ROOT])
    assert len(main.store.load_invoices()) == before


def test_new_invoice_is_saved_in_database_not_in_file(env):
    main, client, data_dir = env
    file_before = (data_dir / "invoices.json").read_text(encoding="utf-8")
    resp = client.post("/invoices", json={
        "seller_name": "Seller BV", "seller_country": "NL", "buyer_name": "New Buyer", "buyer_country": "NL",
        "items": [{"description": "Consulting", "quantity": 1, "unit_price": 100}],
    })
    assert resp.status_code == 201, resp.text
    new_id = resp.json()["id"]

    assert (data_dir / "invoices.json").read_text(encoding="utf-8") == file_before
    stored = [i for i in main.store.load_invoices() if i["id"] == new_id]
    assert len(stored) == 1
    assert client.get(f"/invoices/{new_id}").status_code == 200


def test_invoice_survives_restart(env):
    """A new process (fresh engine) still sees the invoice: nothing lives in memory or /tmp files."""
    main, client, _ = env
    from sqlalchemy import create_engine, select
    new_id = client.post("/invoices", json={
        "seller_name": "S", "seller_country": "NL", "buyer_name": "B", "buyer_country": "NL",
        "items": [{"description": "x", "quantity": 1, "unit_price": 1}],
    }).json()["id"]
    engine = create_engine(main.store.get_engine().url)
    with engine.connect() as conn:
        ids = {r.id for r in conn.execute(select(main.store.invoices_table.c.id))}
    engine.dispose()
    assert new_id in ids


def test_same_stripe_payment_twice_is_counted_once(env):
    main, client, _ = env
    intent = f"pi_{uuid.uuid4().hex}"
    first = client.post("/webhooks/stripe", json=_stripe_event("sess_a", intent))
    assert first.status_code == 200, first.text
    replay = client.post("/webhooks/stripe", json=_stripe_event("sess_a", intent))
    assert replay.status_code == 200
    # Same payment sent for another session must not pay that session too.
    other = client.post("/webhooks/stripe", json=_stripe_event("sess_b", intent))
    assert other.json().get("duplicate") is True

    invoices = [i for i in main.store.load_invoices() if i.get("stripe_intent_id") == intent]
    payments = [p for p in main.store.list_payments() if p["provider_ref"] == intent]
    assert len(invoices) == 1
    assert len(payments) == 1
    sessions = {s["id"]: s for s in main.store.load_sessions()}
    assert sessions["sess_a"]["status"] == "paid"
    assert sessions["sess_b"]["status"] == "created"


def test_same_blockchain_tx_twice_is_counted_once(env):
    main, client, _ = env
    tx = "0x" + uuid.uuid4().hex
    assert client.post("/webhooks/web3", json=_web3_event("sess_c", tx)).status_code == 200
    # Same transaction, different capitalisation, for another session.
    dup = client.post("/webhooks/web3", json=_web3_event("sess_d", tx.upper().replace("0X", "0x")))
    assert dup.json().get("duplicate") is True

    assert len([t for t in main.store.list_blockchain_txs() if t["tx_hash"] == tx.lower()]) == 1
    assert len([i for i in main.store.load_invoices() if (i.get("blockchain_tx_id") or "").lower() == tx]) == 1
    assert {s["id"]: s for s in main.store.load_sessions()}["sess_d"]["status"] == "created"


def test_imported_payments_are_not_counted_again(env):
    main, client, _ = env
    sessions = main.store.load_sessions()
    sessions.append(dict(OLD_SESSIONS[0], id="sess_replay"))
    main.store.save_sessions(sessions)
    before = len(main.store.load_invoices())

    stripe = client.post("/webhooks/stripe", json=_stripe_event("sess_replay", "pi_old_1"))
    web3 = client.post("/webhooks/web3", json=_web3_event("sess_replay", "0xabcdef0001"))
    assert stripe.json().get("duplicate") is True
    assert web3.json().get("duplicate") is True
    assert len(main.store.load_invoices()) == before


def test_store_claims_are_idempotent(env):
    main, _, _ = env
    ref = f"ref_{uuid.uuid4().hex}"
    assert main.store.claim_payment("coinbase", ref) is True
    assert main.store.claim_payment("coinbase", ref) is False
    # Same reference at a different provider is a different payment.
    assert main.store.claim_payment("paypal", ref) is True


def test_uses_requested_database(env):
    main, _, _ = env
    expected = "postgresql" if os.getenv("TEST_DATABASE_URL") else "sqlite"
    assert main.store.get_engine().dialect.name == expected
