# Phase 2: Payment Reality Implementation

## Overview

Phase 2 plugs real payment providers into your hosted checkout framework. The key insight:

**Customer pays via payment provider → webhook sent → session marked PAID → API keys unlocked**

## Architecture

### State Machine

Every session follows this state progression:

```
created → pending → paid → failed
```

- **created**: Session initialized, no payment activity
- **pending**: Payment in progress (optional intermediate state)
- **paid**: Payment confirmed, terminal state → auto-unlock API keys
- **failed**: Payment failed or cancelled, terminal state

### Payment Flow

```
1. Merchant calls POST /create_session with API key
   Returns: session_id, hosted_checkout_url
   Session status: "created", payment_status: "not_started"

2. Customer clicks checkout link
   Opens: https://api.apiblockchain.io/checkout?session={id}

3. Customer pays via One.com / Stripe / Web3

4. Payment provider sends webhook to:
   - POST /webhooks/onecom
   - POST /webhooks/stripe
   - POST /webhooks/web3

5. Webhook handler:
   ✓ Validates session exists
   ✓ Checks state transition is valid
   ✓ Marks session as "paid"
   ✓ Creates invoice record
   ✓ AUTO-GENERATES API key for merchant
   ✓ Generates 7-day customer access link
   ✓ Logs audit event

6. Customer receives:
   - Email with API key (if configured)
   - Access link to download invoice
   - Link to developer dashboard
```

## New Endpoints

### Session Management

#### `POST /create_session`
Create a payment session.

**Request:**
```json
{
  "amount": 99.99,
  "mode": "test",
  "success_url": "https://your-store.com/order/confirm",
  "cancel_url": "https://your-store.com/cart",
  "customer_email": "customer@example.com",
  "customer_name": "John Doe"
}
```

**Response:**
```json
{
  "success": true,
  "id": "session_id_uuid",
  "url": "https://api.apiblockchain.io/checkout?session=session_id_uuid",
  "session": {
    "id": "session_id_uuid",
    "merchant_id": 1,
    "amount": 99.99,
    "mode": "test",
    "status": "created",
    "payment_status": "not_started",
    "metadata": {
      "customer_email": "customer@example.com",
      "customer_name": "John Doe",
      "webhook_sources": []
    },
    "created_at": "2026-02-08T15:28:00.000Z"
  }
}
```

#### `GET /session/{session_id}/status`
Public endpoint to check payment status (no auth required).

**Response:**
```json
{
  "session_id": "session_id_uuid",
  "status": "paid",
  "payment_status": "completed",
  "payment_provider": "stripe",
  "paid_at": "2026-02-08T15:30:00.000Z",
  "amount": 99.99,
  "created_at": "2026-02-08T15:28:00.000Z"
}
```

### Webhook Endpoints

#### `POST /webhooks/stripe`
Stripe webhook handler (for `payment_intent.succeeded` events).

**Payload Example:**
```json
{
  "type": "payment_intent.succeeded",
  "data": {
    "object": {
      "id": "pi_stripe_intent_id",
      "metadata": {
        "session_id": "session_id_uuid"
      }
    }
  }
}
```

**Response on Success:**
```json
{
  "success": true,
  "session_id": "session_id_uuid",
  "invoice": {
    "id": "invoice_uuid",
    "merchant_id": 1,
    "amount": 99.99,
    "payment_provider": "stripe",
    "status": "paid",
    "created_at": "2026-02-08T15:30:00.000Z"
  },
  "api_key_generated": 4,
  "customer_access": {
    "token": "eyJ...",
    "expires_at": "2026-02-15T15:30:00.000Z",
    "access_url": "https://api.apiblockchain.io/access/session_id_uuid?token=..."
  }
}
```

#### `POST /webhooks/onecom`
One.com webhook handler (payment.completed event).

**Payload Example:**
```json
{
  "event": "payment.completed",
  "reference": "session_id_uuid",
  "amount": 99.99,
  "currency": "EUR",
  "merchant_id": 1,
  "payload": {
    "txn_id": "onecom_transaction_id"
  }
}
```

**Response:** Same as Stripe webhook response.

#### `POST /webhooks/web3`
Web3 webhook handler (blockchain payment verification).

**Payload Example:**
```json
{
  "event": "payment.confirmed",
  "session_id": "session_id_uuid",
  "amount": 1.5,
  "blockchain_tx_id": "0xabc123def456...",
  "network": "ethereum"
}
```

**Response:** Includes `blockchain_tx` field with transaction ID.

## What Happens on Payment

When webhook confirms payment, the system automatically:

### 1. Mark Session as Paid
```
status: "created" → "paid"
payment_status: "not_started" → "completed"
paid_at: "2026-02-08T15:30:00.000Z"
payment_provider: "stripe" | "onecom" | "web3"
```

### 2. Create Invoice Record
```json
{
  "id": "invoice_uuid",
  "session_id": "session_id_uuid",
  "merchant_id": 1,
  "amount": 99.99,
  "mode": "test",
  "status": "paid",
  "payment_provider": "stripe",
  "stripe_intent_id": "pi_...",
  "created_at": "2026-02-08T15:30:00.000Z"
}
```

### 3. Auto-Generate API Key
```json
{
  "id": 4,
  "merchant_id": 1,
  "key": "sk_test_<random_suffix>",
  "label": "Auto-generated from session abc123...",
  "mode": "test",
  "created_at": "2026-02-08T15:30:00.000Z"
}
```

**Important:** The API key is auto-generated in **test mode** by default. Merchants can:
- Upgrade to live mode via dashboard
- Rotate/revoke keys
- Create multiple keys with custom labels

### 4. Generate Customer Access Link
7-day JWT token allowing customer to:
- View session details
- Download invoice
- Access refund/support portal

```json
{
  "token": "eyJhbGc...",
  "expires_at": "2026-02-15T15:30:00.000Z",
  "access_url": "https://api.apiblockchain.io/access/session_id?token=..."
}
```

## Database Impact

### Sessions Table (`sessions.json`)
```json
{
  "id": "uuid",
  "merchant_id": 1,
  "amount": 99.99,
  "mode": "test",
  "status": "created",
  "payment_status": "not_started",
  "success_url": "...",
  "cancel_url": "...",
  "url": "https://api.apiblockchain.io/checkout?session=...",
  "created_at": "2026-02-08T15:28:00.000Z",
  "paid_at": "2026-02-08T15:30:00.000Z",
  "payment_provider": "stripe",
  "stripe_intent_id": "pi_...",
  "metadata": {
    "customer_email": "customer@example.com",
    "customer_name": "John Doe",
    "webhook_sources": ["stripe"]
  }
}
```

### Invoices Table (`invoices.json`)
```json
{
  "id": "uuid",
  "session_id": "session_uuid",
  "merchant_id": 1,
  "amount": 99.99,
  "mode": "test",
  "status": "paid",
  "payment_provider": "stripe",
  "stripe_intent_id": "pi_...",
  "created_at": "2026-02-08T15:30:00.000Z"
}
```

### API Keys Table (`api_keys.json`)
```json
{
  "id": 4,
  "merchant_id": 1,
  "key": "sk_test_...",
  "label": "Auto-generated from session abc123",
  "mode": "test",
  "created_at": "2026-02-08T15:30:00.000Z"
}
```

## Audit Logging

All payment events logged to `audit.log`:

```
2026-02-08T15:30:00Z | - | - | WEBHOOK_STRIPE_SUCCESS session_id=session_uuid amount=99.99
2026-02-08T15:30:01Z | - | - | API_KEY_CREATED merchant_id=1
```

## Error Handling

| Scenario | Response | Reason |
|----------|----------|--------|
| Session not found | 404 | Webhook reference doesn't match any session |
| Session already paid | 200 + message | Idempotent: webhook retried, safely ignored |
| Invalid state transition | 409 | Session already failed/paid, no transitions allowed |
| Persistence error | 500 | File system or database issue |
| Read-only filesystem | 503 | Webhook received but can't persist |

## Testing

Run the Phase 2 test suite:

```bash
python test_phase2_webhooks.py
```

Expected output:
```
✓ Session created with payment_status
✓ Stripe webhook processed
✓ One.com webhook processed
✓ Web3 webhook processed
✓ Session status endpoint working
✓ State machine validated
✓ API keys endpoint working
```

## Next Phase (Phase 3): Real Integrations

To move to production, you need to:

1. **Connect Stripe Checkout**
   - Client-side: Create payment intent via `/create_intent`
   - Set `metadata.session_id` in intent
   - Stripe sends webhook to your `/webhooks/stripe`

2. **Connect One.com API**
   - Configure One.com to POST to `/webhooks/onecom`
   - One.com sends `event=payment.completed` with session reference

3. **Secure Webhooks**
   - Add signature verification for Stripe (HMAC-SHA256)
   - Add signature verification for One.com (if provided)
   - Store webhook signing secrets in env vars

4. **Email Integration**
   - Send customer access link + API key after payment
   - Send receipt/invoice PDF

5. **Dashboard Integration**
   - Show total revenue (SUM of paid sessions)
   - Show paid sessions list
   - Add key rotation UI

6. **End-to-End Testing**
   - Test Stripe test mode payments
   - Test One.com sandbox payments
   - Test Web3 transaction verification

## Files Modified

- [main.py](main.py) - Added payment state machine, 3 webhook handlers, auto-key generation
- [test_phase2_webhooks.py](test_phase2_webhooks.py) - Comprehensive webhook test suite

## Summary

Phase 2 answer: **"Can money move, and can we react to it?"**

✅ **YES.**

- Money arrives via Stripe, One.com, or Web3
- You react via webhooks
- Sessions auto-transition to PAID state
- Invoices auto-created
- API keys auto-unlocked
- Customers auto-granted access

The system is now **payment-aware** and **entitlement-ready**. All that remains is plugging in the actual payment provider integrations (Phase 3).
