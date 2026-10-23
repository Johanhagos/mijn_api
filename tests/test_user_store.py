"""Users, API keys, logos and invoice PDFs live in the database and survive a redeploy
(a restart with an empty DATA_DIR, which is what Railway does to /tmp).

Runs against SQLite by default. Set TEST_DATABASE_URL to run against PostgreSQL.
"""
import base64
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

PNG = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==")
ADMIN = {"name": "store_admin@example.com", "password": "admin-pass-123"}


def _boot(mp, data_dir, db_url):
    """Import main as a fresh process would: new engine, given DATA_DIR."""
    import app.store as store
    if store._engine is not None:
        store._engine.dispose()
    store._engine = None
    store._engine_url = None
    mp.setenv("DATA_DIR", str(data_dir))
    mp.setenv("DATABASE_URL", db_url)
    import main
    importlib.reload(main)
    return main, TestClient(main.app)


def _reset_store_tables(db_url):
    """Each test module starts from an empty database (TEST_DATABASE_URL is shared)."""
    from sqlalchemy import create_engine
    import app.store as store
    if store._engine is not None:
        store._engine.dispose()
    store._engine = None
    store._engine_url = None
    engine = create_engine(db_url)
    store.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture(scope="module")
def env(tmp_path_factory):
    from passlib.context import CryptContext
    hashed = CryptContext(schemes=["bcrypt"]).hash(ADMIN["password"])
    data_dir = tmp_path_factory.mktemp("data")
    (data_dir / "users.json").write_text(json.dumps([
        {"id": 9001, "name": ADMIN["name"], "password": hashed, "role": "admin"},
    ]), encoding="utf-8")

    mp = pytest.MonkeyPatch()
    mp.delenv("RAILWAY_ENVIRONMENT", raising=False)
    db_url = os.getenv("TEST_DATABASE_URL") or f"sqlite:///{(data_dir / 'users-test.db').as_posix()}"
    _reset_store_tables(db_url)
    main, client = _boot(mp, data_dir, db_url)
    yield {"mp": mp, "db_url": db_url, "main": main, "client": client, "tmp": tmp_path_factory}
    mp.undo()


def _login(client, name, password):
    resp = client.post("/login", json={"name": name, "password": password})
    assert resp.status_code == 200, resp.text
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


def test_everything_survives_a_redeploy(env, give_plan):
    main, client = env["main"], env["client"]
    name = f"merchant_{uuid.uuid4().hex[:8]}"
    reg = client.post("/register", json={"name": name, "email": f"{name}@example.com",
                                         "password": "merchant-pass-1", "business_name": "Shop", "country": "NL"})
    assert reg.status_code in (200, 201), reg.text
    give_plan(name)
    auth = _login(client, name, "merchant-pass-1")

    key = client.post("/api-keys", json={"label": "shop", "mode": "test"}, headers=auth)
    assert key.status_code in (200, 201), key.text
    logo = client.post("/merchant/logo", files={"file": ("logo.png", PNG, "image/png")}, headers=auth)
    assert logo.status_code == 200, logo.text
    inv = client.post("/invoices", headers=auth, json={
        "seller_name": "Shop", "seller_country": "NL", "buyer_name": "Buyer", "buyer_country": "NL",
        "items": [{"description": "Item", "quantity": 1, "unit_price": 50}]})
    assert inv.status_code == 201, inv.text
    pdf_before = client.get(f"/invoices/{inv.json()['id']}/pdf", headers=auth).content
    assert pdf_before.startswith(b"%PDF")

    # Redeploy: brand-new empty DATA_DIR, same database.
    main, client = _boot(env["mp"], env["tmp"].mktemp("redeploy"), env["db_url"])
    auth = _login(client, name, "merchant-pass-1")
    keys = client.get("/api-keys", headers=auth).json()
    assert any(k["id"] == key.json()["id"] for k in keys)
    logo_url = client.get("/merchant/logo", headers=auth).json()["logo_url"]
    served = client.get(logo_url)
    assert served.status_code == 200 and served.content == PNG
    assert served.headers["content-type"] == "image/png"
    pdf_after = client.get(f"/invoices/{inv.json()['id']}/pdf", headers=auth).content
    assert pdf_after == pdf_before  # the issued PDF, not a regenerated one
    env["main"], env["client"] = main, client


def test_users_are_not_overwritten_from_repo_on_start(env):
    main = env["main"]
    names = {u["name"] for u in main.store.load_users()}
    assert ADMIN["name"] in names
    assert not (Path(os.environ["DATA_DIR"]) / "users.json").exists()


def test_deleted_user_and_revoked_key_stay_deleted(env, give_plan):
    main, client = env["main"], env["client"]
    admin = _login(client, ADMIN["name"], ADMIN["password"])
    name = f"tmp_{uuid.uuid4().hex[:8]}"
    client.post("/register", json={"name": name, "email": f"{name}@example.com", "password": "tmp-pass-12345"})
    give_plan(name)
    auth = _login(client, name, "tmp-pass-12345")
    key_id = client.post("/api-keys", json={"label": "x"}, headers=auth).json()["id"]
    assert client.delete(f"/api-keys/{key_id}", headers=auth).status_code == 200
    assert all(str(k["id"]) != str(key_id) for k in main.store.load_api_keys())

    user_id = next(u["id"] for u in main.store.load_users() if u["name"] == name)
    assert client.delete(f"/admin/users/{user_id}", headers=admin).status_code == 200
    assert all(u["name"] != name for u in main.store.load_users())


def test_same_new_id_cannot_overwrite_another_user(env):
    main = env["main"]
    users = main.store.load_users()
    taken = users[0]
    with pytest.raises(main.store.StoreConflict):
        main.store.save_users([dict(taken, name="someone_else@example.com")])
    assert any(u["name"] == taken["name"] for u in main.store.load_users())


def test_logo_rejects_other_files(env):
    client = env["client"]
    auth = _login(client, ADMIN["name"], ADMIN["password"])
    bad = client.post("/merchant/logo", files={"file": ("evil.html", b"<script>", "image/png")}, headers=auth)
    assert bad.status_code == 400
    assert client.get("/merchant/logos/..%2Fusers.json").status_code == 404


def test_vat_cross_border_eu(env):
    main = env["main"]
    rate, reverse, _ = main.determine_tax_rate("NL", "DE", "DE123456789")
    assert (rate, reverse) == (0.0, True)
    rate, reverse, _ = main.determine_tax_rate("NL", "DE", None)
    assert reverse is False and rate == main.EU_COUNTRIES.get("NL", 21.0)
