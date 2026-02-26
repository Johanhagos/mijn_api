import requests
import uuid
import pytest

BASE_URL = "http://127.0.0.1:8000"
API_KEY = "sk_test_local_automation"


def pytest_configure(config):
    # Ensure tests that rely on JWT secret can sign tokens if needed
    import os
    if not os.getenv("JWT_SECRET_KEY"):
        os.environ["JWT_SECRET_KEY"] = "testsecret"


@pytest.fixture(scope="module")
def session_id():
    """Create a session via the running app and return its id for webhook tests."""
    headers = {"X-API-Key": API_KEY, "Content-Type": "application/json"}
    payload = {
        "amount": 5.0,
        "mode": "test",
        "success_url": "https://example.test/success",
        "cancel_url": "https://example.test/cancel",
        "customer_email": "test@example.com",
        "customer_name": "Test User"
    }
    try:
        r = requests.post(f"{BASE_URL}/create_session", headers=headers, json=payload, timeout=5)
        if r.status_code == 200:
            data = r.json()
            return data.get("id")
    except Exception:
        # fallback: generate a random UUID so tests that accept None can continue
        return str(uuid.uuid4())
