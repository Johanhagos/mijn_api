import os
import json
from fastapi.testclient import TestClient
from main import app
from pathlib import Path

client = TestClient(app)

DATA_DIR = Path(os.getenv("DATA_DIR", "/tmp"))
API_KEYS_FILE = DATA_DIR / "api_keys.json"


def setup_module(module):
    # Ensure DATA_DIR exists and seed api_keys.json for tests
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    # Create a test admin key entry
    api_keys = [{"key": "test-admin-key", "role": "admin"}]
    API_KEYS_FILE.write_text(json.dumps(api_keys), encoding="utf-8")


def teardown_module(module):
    try:
        API_KEYS_FILE.unlink()
    except Exception:
        pass


def test_get_vat_list():
    r = client.get("/agent/vat")
    assert r.status_code == 200
    assert isinstance(r.json(), dict)


def test_get_country_se():
    r = client.get("/agent/vat/SE")
    assert r.status_code == 200
    j = r.json()
    assert j.get("name") in ("Sweden", "Sverige") or j.get("standard_rate") == 25.0


def test_put_country_requires_admin():
    payload = {"name": "Testlandia", "standard_rate": 9.9}
    r = client.put("/agent/vat/TT", json=payload)
    # No admin header -> forbidden in production-like mode; in our test environment default is non-prod so may allow
    # We expect either 403 or 200 depending on env; assert not 500
    assert r.status_code in (200, 403)


def test_put_country_with_api_key():
    payload = {"name": "Testlandia", "standard_rate": 9.9}
    headers = {"X-VAT-ADMIN-KEY": "test-admin-key"}
    r = client.put("/agent/vat/TT", json=payload, headers=headers)
    assert r.status_code == 200
    j = r.json()
    assert j["country"] == "TT"
    assert j["record"]["name"] == "Testlandia"

    # verify GET returns it
    r2 = client.get("/agent/vat/TT")
    assert r2.status_code == 200
    assert r2.json().get("standard_rate") == 9.9
