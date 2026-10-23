"""Each merchant has their own invoices: they only list, open, change and download their
own, numbering runs per merchant, and only an admin can see every merchant's invoices.
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

ADMIN = {"name": "iso_admin@example.com", "password": "admin-pass-123"}
# Invoice from before merchant_id was stored: owned through created_by
LEGACY = {"id": "legacy-inv", "invoice_number": "INV-2026-0041", "seller_name": "Old Shop", "buyer_name": "B",
          "subtotal": 10, "vat_amount": 0, "total": 10, "status": "issued", "created_by": "legacy_merchant"}


@pytest.fixture(scope="module")
def env(tmp_path_factory, give_plan):
    from passlib.context import CryptContext
    hasher = CryptContext(schemes=["bcrypt"])
    data_dir = tmp_path_factory.mktemp("data")
    (data_dir / "users.json").write_text(json.dumps([
        {"id": 8001, "name": ADMIN["name"], "password": hasher.hash(ADMIN["password"]), "role": "admin"},
        {"id": 8002, "name": "legacy_merchant", "password": hasher.hash("legacy-pass-1"), "role": "user"},
    ]), encoding="utf-8")
    (data_dir / "invoices.json").write_text(json.dumps([LEGACY]), encoding="utf-8")
    mp = pytest.MonkeyPatch()
    mp.delenv("RAILWAY_ENVIRONMENT", raising=False)
    mp.setenv("DATA_DIR", str(data_dir))
    mp.setenv("DATABASE_URL", os.getenv("TEST_DATABASE_URL") or f"sqlite:///{(data_dir / 'iso.db').as_posix()}")
    import app.store as store
    if store._engine is not None:
        store._engine.dispose()
    store._engine, store._engine_url = None, None
    from sqlalchemy import create_engine
    eng = create_engine(os.environ["DATABASE_URL"]); store.metadata.drop_all(eng); eng.dispose()

    import main
    importlib.reload(main)
    client = TestClient(main.app)
    give_plan("legacy_merchant")
    yield {"client": client, "admin": _login(client, ADMIN["name"], ADMIN["password"]),
           "a": _merchant(client, give_plan), "b": _merchant(client, give_plan),
           "legacy": _login(client, "legacy_merchant", "legacy-pass-1")}
    mp.undo()


def _login(client, name, password):
    r = client.post("/login", json={"name": name, "password": password})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def _merchant(client, give_plan):
    name = f"merchant_{uuid.uuid4().hex[:6]}"
    client.post("/register", json={"name": name, "email": f"{name}@example.com", "password": "merchant-pass-1"})
    give_plan(name)
    return _login(client, name, "merchant-pass-1")


def _invoice(env, who, buyer="Buyer"):
    r = env["client"].post("/invoices", headers=env[who], json={
        "seller_name": "Shop", "seller_country": "NL", "buyer_name": buyer, "buyer_country": "NL",
        "items": [{"description": "x", "quantity": 1, "unit_price": 10}], "vat_rate": 0})
    assert r.status_code == 201, r.text
    return r.json()


def _ids(env, who, query=""):
    r = env["client"].get(f"/invoices{query}", headers=env[who])
    assert r.status_code == 200, r.text
    return {i["id"] for i in r.json()}


def test_merchants_only_list_their_own_invoices(env):
    a = _invoice(env, "a", "Buyer of A")
    b = _invoice(env, "b", "Buyer of B")
    assert a["id"] in _ids(env, "a") and b["id"] not in _ids(env, "a")
    assert b["id"] in _ids(env, "b") and a["id"] not in _ids(env, "b")
    assert LEGACY["id"] not in _ids(env, "a")


def test_other_merchants_invoice_is_not_found(env):
    c, a = env["client"], _invoice(env, "a")
    url = f"/invoices/{a['id']}"
    assert c.get(url, headers=env["b"]).status_code == 404
    assert c.get(f"{url}/pdf", headers=env["b"]).status_code == 404
    assert c.patch(url, headers=env["b"], json={"notes": "hijacked"}).status_code == 404
    assert c.post(f"{url}/void", headers=env["b"]).status_code == 404
    assert c.get(f"{url}/credit-notes", headers=env["b"]).status_code == 404
    assert c.post("/credit-notes", headers=env["b"], json={
        "invoice_id": a["id"], "amount": 1, "reason": "full_refund"}).status_code == 404
    # Untouched, and still fine for its owner
    own = c.get(url, headers=env["a"])
    assert own.status_code == 200 and own.json()["notes"] != "hijacked" and own.json()["status"] != "void"
    assert c.get(f"{url}/pdf", headers=env["a"]).status_code == 200


def test_numbering_runs_per_merchant(env):
    first_a = _invoice(env, "a")["invoice_number"]
    first_b = _invoice(env, "b")["invoice_number"]
    next_a = _invoice(env, "a")["invoice_number"]
    num = lambda n: int(n.rsplit("-", 1)[1])
    assert num(next_a) == num(first_a) + 1
    # Merchant B's numbers do not move merchant A's sequence, and vice versa
    assert num(first_b) <= num(first_a)


def test_legacy_invoice_belongs_to_its_creator(env):
    assert LEGACY["id"] in _ids(env, "legacy")
    assert env["client"].get(f"/invoices/{LEGACY['id']}", headers=env["legacy"]).status_code == 200
    # Numbering continues after the merchant's own old invoices
    assert _invoice(env, "legacy")["invoice_number"].endswith("-0042")


def test_admin_lists_own_by_default_and_everything_with_all(env):
    a = _invoice(env, "a")
    assert a["id"] not in _ids(env, "admin")
    assert {a["id"], LEGACY["id"]} <= _ids(env, "admin", "?all=true")
    assert env["client"].get(f"/invoices/{a['id']}", headers=env["admin"]).status_code == 200
    # ?all is ignored for merchants
    assert LEGACY["id"] not in _ids(env, "a", "?all=true")
