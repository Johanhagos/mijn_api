"""
Test Phase 2 Payment Processing
Tests payment session creation, webhook handling, and customer access token generation.
"""

import pytest
import json
from datetime import datetime, timezone
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from main_phase1 import app
from db import get_db
from models_phase1 import Base, Organization, User, PaymentSession
from payment import (
    validate_payment_state_transition,
    generate_api_key,
    generate_customer_access_link
)

# ===== TEST DATABASE SETUP =====

# Use in-memory SQLite for testing
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base.metadata.create_all(bind=engine)

def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)


# ===== FIXTURES =====

@pytest.fixture
def setup_test_org_and_user():
    """Create a test organization and user."""
    db = TestingSessionLocal()
    
    # Create organization
    org = Organization(
        name="Test Org",
        email="test@example.com",
        country="NL",
        vat_number="NL123456789B01"
    )
    db.add(org)
    db.commit()
    db.refresh(org)
    
    # Create user
    from auth import hash_password
    user = User(
        name="testuser",
        email="testuser@example.com",
        password=hash_password("testpass123"),
        role="admin",
        org_id=org.id,
        email_verified=True
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    
    db.close()
    return org, user


@pytest.fixture
def auth_headers(setup_test_org_and_user):
    """Get authorization headers for test user."""
    org, user = setup_test_org_and_user
    
    # Login and get token
    response = client.post(
        "/login",
        json={"name": "testuser", "password": "testpass123"}
    )
    assert response.status_code == 200
    token = response.json()["access_token"]
    
    return {"Authorization": f"Bearer {token}"}


# ===== TEST STATE MACHINE =====

class TestStateMachine:
    """Test payment state machine validation."""
    
    def test_valid_transitions(self):
        """Test allowed state transitions."""
        # created → paid (direct payment)
        assert validate_payment_state_transition("created", "paid") is True
        
        # created → pending (async payment)
        assert validate_payment_state_transition("created", "pending") is True
        
        # created → failed (payment failed)
        assert validate_payment_state_transition("created", "failed") is True
        
        # pending → paid
        assert validate_payment_state_transition("pending", "paid") is True
        
        # pending → failed
        assert validate_payment_state_transition("pending", "failed") is True
    
    def test_invalid_transitions(self):
        """Test disallowed state transitions."""
        # paid → anything (terminal state)
        assert validate_payment_state_transition("paid", "pending") is False
        assert validate_payment_state_transition("paid", "failed") is False
        assert validate_payment_state_transition("paid", "created") is False
        
        # failed → anything (terminal state)
        assert validate_payment_state_transition("failed", "paid") is False
        assert validate_payment_state_transition("failed", "pending") is False
        
        # Invalid states
        assert validate_payment_state_transition("unknown", "paid") is False
        assert validate_payment_state_transition("created", "unknown") is False


# ===== TEST API KEY GENERATION =====

class TestAPIKeyGeneration:
    """Test API key generation."""
    
    def test_api_key_format(self):
        """Test generated API key has correct format."""
        api_key = generate_api_key()
        
        # Check prefix
        assert api_key.startswith("sk_test_")
        
        # Check length
        assert len(api_key) == len("sk_test_") + 32
        
        # Check characters are valid
        valid_chars = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789")
        for char in api_key.split("_", 1)[1]:  # Skip prefix
            assert char in valid_chars
    
    def test_api_keys_are_unique(self):
        """Test that generated API keys are unique."""
        keys = set()
        for _ in range(100):
            key = generate_api_key()
            assert key not in keys
            keys.add(key)


# ===== TEST PAYMENT ENDPOINTS =====

class TestPaymentEndpoints:
    """Test payment endpoints."""
    
    def test_create_payment_session_success(self, auth_headers):
        """Test successful payment session creation."""
        response = client.post(
            "/create_session",
            json={
                "amount_cents": 10000,
                "currency": "EUR",
                "success_url": "https://example.com/success",
                "cancel_url": "https://example.com/cancel"
            },
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Check response fields
        assert "session_id" in data
        assert "checkout_url" in data
        assert data["amount_cents"] == 10000
        assert data["currency"] == "EUR"
        assert data["status"] == "created"
        assert data["payment_status"] == "not_started"
        assert data["checkout_url"].startswith("/checkout?session_id=")
    
    def test_create_payment_session_unauthorized(self):
        """Test creating payment session without authentication."""
        response = client.post(
            "/create_session",
            json={
                "amount_cents": 10000,
                "currency": "EUR"
            }
        )
        
        assert response.status_code == 403
    
    def test_create_payment_session_invalid_amount(self, auth_headers):
        """Test creating payment session with invalid amount."""
        response = client.post(
            "/create_session",
            json={
                "amount_cents": 0,  # Invalid: must be > 0
                "currency": "EUR"
            },
            headers=auth_headers
        )
        
        assert response.status_code == 422  # Validation error
    
    def test_get_session_status(self, auth_headers):
        """Test getting session status (public endpoint)."""
        # Create session first
        create_response = client.post(
            "/create_session",
            json={
                "amount_cents": 5000,
                "currency": "USD"
            },
            headers=auth_headers
        )
        
        session_id = create_response.json()["session_id"]
        
        # Get status (no auth required)
        status_response = client.get(f"/session/{session_id}/status")
        
        assert status_response.status_code == 200
        data = status_response.json()
        assert data["session_id"] == session_id
        assert data["status"] == "created"
        assert data["amount_cents"] == 5000
        assert data["currency"] == "USD"
    
    def test_get_session_status_not_found(self):
        """Test getting status for non-existent session."""
        response = client.get("/session/nonexistent/status")
        assert response.status_code == 404


# ===== TEST WEBHOOK HANDLERS =====

class TestWebhookHandlers:
    """Test webhook event handlers."""
    
    def test_stripe_webhook_success(self, auth_headers):
        """Test Stripe webhook processing."""
        # Create session first
        create_response = client.post(
            "/create_session",
            json={"amount_cents": 20000, "currency": "EUR"},
            headers=auth_headers
        )
        session_id = create_response.json()["session_id"]
        
        # Simulate Stripe webhook
        webhook_payload = {
            "type": "payment_intent.succeeded",
            "data": {
                "object": {
                    "id": "pi_stripe_123",
                    "metadata": {"session_id": session_id}
                }
            }
        }
        
        response = client.post(
            "/webhooks/stripe",
            json=webhook_payload
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["session_id"] == session_id
        assert "api_key_created" in data
        assert "customer_access" in data
        
        # Verify session status updated
        status_response = client.get(f"/session/{session_id}/status")
        status_data = status_response.json()
        assert status_data["status"] == "paid"
        assert status_data["payment_provider"] == "stripe"
    
    def test_onecom_webhook_success(self, auth_headers):
        """Test One.com webhook processing."""
        # Create session
        create_response = client.post(
            "/create_session",
            json={"amount_cents": 15000, "currency": "EUR"},
            headers=auth_headers
        )
        session_id = create_response.json()["session_id"]
        
        # Simulate One.com webhook
        webhook_payload = {
            "type": "payment.completed",
            "reference": session_id,
            "transaction_id": "txn_onecom_456",
            "status": "completed"
        }
        
        response = client.post(
            "/webhooks/onecom",
            json=webhook_payload
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["session_id"] == session_id
        assert "api_key_created" in data
        
        # Verify session updated
        status_response = client.get(f"/session/{session_id}/status")
        status_data = status_response.json()
        assert status_data["payment_provider"] == "onecom"
    
    def test_web3_webhook_success(self, auth_headers):
        """Test Web3 webhook processing."""
        # Create session
        create_response = client.post(
            "/create_session",
            json={"amount_cents": 30000, "currency": "EUR"},
            headers=auth_headers
        )
        session_id = create_response.json()["session_id"]
        
        # Simulate Web3 webhook
        webhook_payload = {
            "type": "payment.confirmed",
            "session_id": session_id,
            "transaction_id": "0x789blockchain",
            "network": "ethereum"
        }
        
        response = client.post(
            "/webhooks/web3",
            json=webhook_payload
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        
        # Verify session
        status_response = client.get(f"/session/{session_id}/status")
        status_data = status_response.json()
        assert status_data["payment_provider"] == "web3"
    
    def test_webhook_double_payment_prevention(self, auth_headers):
        """Test that webhooks prevent double-charging via state machine."""
        # Create session and process payment
        create_response = client.post(
            "/create_session",
            json={"amount_cents": 10000, "currency": "EUR"},
            headers=auth_headers
        )
        session_id = create_response.json()["session_id"]
        
        # First webhook payment
        webhook_payload = {
            "type": "payment_intent.succeeded",
            "data": {
                "object": {
                    "id": "pi_123",
                    "metadata": {"session_id": session_id}
                }
            }
        }
        
        response1 = client.post("/webhooks/stripe", json=webhook_payload)
        assert response1.status_code == 200
        assert response1.json()["success"] is True
        
        # Attempt duplicate payment (should fail)
        response2 = client.post("/webhooks/stripe", json=webhook_payload)
        assert response2.status_code == 200
        # Should reject due to state machine (already paid)
        assert response2.json()["success"] is False
        assert "Invalid state transition" in response2.json()["message"]
    
    def test_webhook_missing_session(self):
        """Test webhook with missing session_id."""
        webhook_payload = {
            "type": "payment_intent.succeeded",
            "data": {
                "object": {
                    "id": "pi_123",
                    "metadata": {}  # No session_id
                }
            }
        }
        
        response = client.post("/webhooks/stripe", json=webhook_payload)
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is False


# ===== TEST CUSTOMER ACCESS TOKENS =====

class TestCustomerAccessTokens:
    """Test customer access token generation."""
    
    def test_customer_access_link_generation(self):
        """Test customer access link structure."""
        session_id = "session_test_123"
        org_id = 1
        
        result = generate_customer_access_link(session_id, org_id)
        
        assert "token" in result
        assert "access_url" in result
        assert "expires_days" in result
        assert result["expires_days"] == 7
        assert result["access_url"].startswith("/customer/session/")
        assert session_id in result["access_url"]
        assert result["token"] in result["access_url"]


# ===== TEST PAYMENT AUDIT TRAIL =====

class TestPaymentAuditTrail:
    """Test that payment events are properly logged."""
    
    def test_payment_session_created_logged(self, auth_headers, setup_test_org_and_user):
        """Test that payment session creation is logged in audit trail."""
        org, user = setup_test_org_and_user
        
        response = client.post(
            "/create_session",
            json={"amount_cents": 25000, "currency": "EUR"},
            headers=auth_headers
        )
        
        assert response.status_code == 200
        
        # Get audit logs
        audit_response = client.get("/audit-logs", headers=auth_headers)
        assert audit_response.status_code == 200
        
        logs = audit_response.json()
        # Find payment session created log
        payment_logs = [log for log in logs if log.get("action") == "PAYMENT_SESSION_CREATED"]
        assert len(payment_logs) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
