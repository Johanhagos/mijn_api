"""
Payment processing utilities for Phase 2
Handles state machine validation, API key generation, and customer access
"""

import secrets
import string
from datetime import datetime, timezone, timedelta
from typing import Optional, Tuple, Dict, Any
from jose import jwt
import os

# ===== CONFIGURATION =====

PAYMENT_STATE_TRANSITIONS = {
    "created": ["pending", "paid", "failed"],
    "pending": ["paid", "failed"],
    "paid": [],  # terminal state
    "failed": [],  # terminal state
}

API_KEY_PREFIX = "sk_"
API_KEY_LENGTH = 32  # characters after prefix

JWT_SECRET = os.getenv("JWT_SECRET_KEY")
CUSTOMER_ACCESS_EXPIRES_DAYS = 7


# ===== STATE MACHINE =====

def validate_payment_state_transition(current_status: str, new_status: str) -> bool:
    """
    Validate if a payment state transition is allowed.
    
    Returns True if transition is valid, False otherwise.
    """
    if current_status not in PAYMENT_STATE_TRANSITIONS:
        return False
    
    allowed_transitions = PAYMENT_STATE_TRANSITIONS[current_status]
    return new_status in allowed_transitions


# ===== API KEY GENERATION =====

def generate_api_key() -> str:
    """
    Generate a random API key.
    Format: sk_test_<32-random-chars> or sk_live_<32-random-chars>
    """
    # Generate random alphanumeric suffix
    charset = string.ascii_letters + string.digits
    random_suffix = ''.join(secrets.choice(charset) for _ in range(API_KEY_LENGTH))
    
    api_key = f"{API_KEY_PREFIX}test_{random_suffix}"
    return api_key


def get_api_key_prefix(api_key: str) -> str:
    """Extract first 8 characters of API key for display."""
    return api_key[:8]


# ===== CUSTOMER ACCESS =====

def generate_customer_access_token(
    session_id: str,
    org_id: int,
    expires_days: int = CUSTOMER_ACCESS_EXPIRES_DAYS
) -> str:
    """
    Generate a JWT token for customer access to session details.
    Token includes session_id and custom claims for the customer.
    """
    expire = datetime.now(timezone.utc) + timedelta(days=expires_days)
    
    payload = {
        "sub": f"customer_{session_id}",
        "session_id": session_id,
        "org_id": org_id,
        "exp": expire,
        "iat": datetime.now(timezone.utc),
        "type": "customer_access"
    }
    
    token = jwt.encode(payload, JWT_SECRET, algorithm="HS256")
    return token


def generate_customer_access_link(
    session_id: str,
    org_id: int,
    base_url: str = "http://localhost:5000"
) -> Dict[str, str]:
    """
    Generate a customer access link with JWT token.
    Customer can use this to view invoice, download receipts, etc.
    """
    token = generate_customer_access_token(session_id, org_id)
    
    access_url = f"{base_url}/customer/session/{session_id}?token={token}"
    
    return {
        "token": token,
        "access_url": access_url,
        "expires_days": CUSTOMER_ACCESS_EXPIRES_DAYS
    }


# ===== WEBHOOK PROCESSING =====

def process_stripe_webhook(webhook_data: Dict[str, Any], session: Dict[str, Any]) -> Dict[str, Any]:
    """
    Process a Stripe webhook.
    
    Validates and extracts payment information from Stripe webhook payload.
    """
    event_type = webhook_data.get("type")
    
    if event_type != "payment_intent.succeeded":
        return {"processed": False, "reason": f"Ignored event type: {event_type}"}
    
    # Extract session_id from metadata
    try:
        payment_intent = webhook_data.get("data", {}).get("object", {})
        session_id = payment_intent.get("metadata", {}).get("session_id")
        intent_id = payment_intent.get("id")
        
        if not session_id:
            return {"processed": False, "reason": "No session_id in metadata"}
        
        return {
            "processed": True,
            "session_id": session_id,
            "provider": "stripe",
            "intent_id": intent_id,
            "amount_cents": payment_intent.get("amount")
        }
    except Exception as e:
        return {"processed": False, "reason": f"Failed to parse: {str(e)}"}


def process_onecom_webhook(webhook_data: Dict[str, Any], session: Dict[str, Any]) -> Dict[str, Any]:
    """
    Process a One.com webhook.
    """
    event_type = webhook_data.get("type")
    
    if event_type != "payment.completed":
        return {"processed": False, "reason": f"Ignored event type: {event_type}"}
    
    try:
        session_id = webhook_data.get("reference")
        txn_id = webhook_data.get("transaction_id")
        
        if not session_id:
            return {"processed": False, "reason": "No reference (session_id) in webhook"}
        
        return {
            "processed": True,
            "session_id": session_id,
            "provider": "onecom",
            "txn_id": txn_id,
            "amount_cents": webhook_data.get("amount")
        }
    except Exception as e:
        return {"processed": False, "reason": f"Failed to parse: {str(e)}"}


def process_web3_webhook(webhook_data: Dict[str, Any], session: Dict[str, Any]) -> Dict[str, Any]:
    """
    Process a Web3/Blockchain webhook.
    """
    event_type = webhook_data.get("type")
    
    if event_type != "payment.confirmed":
        return {"processed": False, "reason": f"Ignored event type: {event_type}"}
    
    try:
        session_id = webhook_data.get("session_id")
        tx_id = webhook_data.get("transaction_id")
        network = webhook_data.get("network", "ethereum")
        
        if not session_id:
            return {"processed": False, "reason": "No session_id in webhook"}
        
        return {
            "processed": True,
            "session_id": session_id,
            "provider": "web3",
            "tx_id": tx_id,
            "network": network,
            "amount_cents": webhook_data.get("amount")
        }
    except Exception as e:
        return {"processed": False, "reason": f"Failed to parse: {str(e)}"}
