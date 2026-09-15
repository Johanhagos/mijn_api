import importlib
import sys
from pathlib import Path

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def test_login_works_without_env_secret_in_dev(monkeypatch, tmp_path):
    app_dir = Path(__file__).resolve().parent.parent
    monkeypatch.delenv("JWT_SECRET_KEY", raising=False)
    monkeypatch.setenv("DATA_DIR", str(tmp_path))

    import main
    importlib.reload(main)

    client = TestClient(main.app)
    response = client.post(
        "/login",
        json={"name": "merchant_test@example.com", "password": "merchant123"},
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["access_token"]
    assert body["token_type"] == "bearer"
