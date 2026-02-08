# Phase 2 Architecture Diagram

## System Overview

```
┌────────────────────────────────────────────────────────────────────────────┐
│                         YOUR API (api.apiblockchain.io)                    │
│                                                                            │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │                    PAYMENT CONTROL PLANE                         │   │
│  │                                                                  │   │
│  │  POST /create_session                                           │   │
│  │  ├─ Validates API key                                           │   │
│  │  ├─ Creates session {id, status="created"}                      │   │
│  │  ├─ Returns checkout URL                                        │   │
│  │  └─ Persists to sessions.json                                   │   │
│  │                                                                  │   │
│  │  GET /checkout?session={id}                                     │   │
│  │  ├─ Renders branded payment form                                │   │
│  │  ├─ Embeds Stripe/One.com/Web3 components                       │   │
│  │  └─ Customer initiates payment                                  │   │
│  │                                                                  │   │
│  │  GET /session/{id}/status                                       │   │
│  │  └─ Public endpoint (no auth) to check if paid                  │   │
│  │                                                                  │   │
│  └──────────────────────────────────────────────────────────────────┘   │
│                                                                            │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │                   WEBHOOK INGESTION (Payment Reaction)           │   │
│  │                                                                  │   │
│  │  POST /webhooks/stripe                                          │   │
│  │  ├─ Event type: payment_intent.succeeded                        │   │
│  │  ├─ Extract session_id from metadata                            │   │
│  │  ├─ Load session from sessions.json                             │   │
│  │  ├─ Validate state transition (created → paid)                  │   │
│  │  ├─ Update session.status = "paid"                              │   │
│  │  ├─ [Auto-create invoice]                                       │   │
│  │  ├─ [Auto-generate API key]                                     │   │
│  │  ├─ [Generate 7-day access token]                               │   │
│  │  ├─ Save to invoices.json, api_keys.json                        │   │
│  │  └─ Return {success, invoice, api_key_id, customer_access}      │   │
│  │                                                                  │   │
│  │  POST /webhooks/onecom                                          │   │
│  │  ├─ Event type: payment.completed                               │   │
│  │  ├─ Reference field = session_id                                │   │
│  │  ├─ Same flow as Stripe webhook                                 │   │
│  │  └─ (Save onecom_txn_id instead of stripe_intent_id)            │   │
│  │                                                                  │   │
│  │  POST /webhooks/web3                                            │   │
│  │  ├─ Event type: payment.confirmed                               │   │
│  │  ├─ Blockchain TX ID + network                                  │   │
│  │  ├─ Same flow as others                                         │   │
│  │  └─ (Save blockchain_tx_id and network)                         │   │
│  │                                                                  │   │
│  └──────────────────────────────────────────────────────────────────┘   │
│                                                                            │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │                   ENTITLEMENT ENGINE                             │   │
│  │                                                                  │   │
│  │  When webhook marks session PAID:                               │   │
│  │  ┌────────────────────────────────────────────────────────┐    │   │
│  │  │ 1. validate_payment_state_transition()                │    │   │
│  │  │    └─ Ensures state change is allowed                 │    │   │
│  │  │                                                         │    │   │
│  │  │ 2. auto_unlock_api_keys()                              │    │   │
│  │  │    ├─ Check if merchant already has key               │    │   │
│  │  │    ├─ If not: generate sk_test_<random>               │    │   │
│  │  │    ├─ Save to api_keys.json                            │    │   │
│  │  │    └─ Key immediately usable                           │    │   │
│  │  │                                                         │    │   │
│  │  │ 3. generate_customer_access_link()                     │    │   │
│  │  │    ├─ Create JWT token (expires 7 days)               │    │   │
│  │  │    ├─ Include customer_{session_id} in "sub"          │    │   │
│  │  │    ├─ Build access URL with token                     │    │   │
│  │  │    └─ Return to webhook                               │    │   │
│  │  │                                                         │    │   │
│  │  │ 4. Create invoice record                               │    │   │
│  │  │    ├─ Link to session_id                               │    │   │
│  │  │    ├─ Record amount & provider                         │    │   │
│  │  │    └─ Persist to invoices.json                         │    │   │
│  │  └────────────────────────────────────────────────────────┘    │   │
│  │                                                                  │   │
│  └──────────────────────────────────────────────────────────────────┘   │
│                                                                            │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │                    PERSISTENCE LAYER                            │   │
│  │                                                                  │   │
│  │  /data/sessions.json                                            │   │
│  │  [{                                                             │   │
│  │    "id": "uuid",                                               │   │
│  │    "merchant_id": 1,                                           │   │
│  │    "status": "paid",       ← State machine                     │   │
│  │    "payment_status": "completed",  ← Webhook tracking         │   │
│  │    "payment_provider": "stripe",   ← Which provider           │   │
│  │    "paid_at": "2026-02-08...",    ← When paid                 │   │
│  │    "stripe_intent_id": "pi_...",  ← Provider ref             │   │
│  │    "metadata": {                   ← Extensible               │   │
│  │      "webhook_sources": ["stripe"]                            │   │
│  │    }                                                           │   │
│  │  }]                                                            │   │
│  │                                                                  │   │
│  │  /data/invoices.json                                            │   │
│  │  [{                                                             │   │
│  │    "id": "uuid",                                               │   │
│  │    "session_id": "uuid",  ← Links to session                  │   │
│  │    "merchant_id": 1,                                           │   │
│  │    "amount": 99.99,                                            │   │
│  │    "payment_provider": "stripe",  ← Provider tracking         │   │
│  │    "created_at": "2026-02-08..."                              │   │
│  │  }]                                                            │   │
│  │                                                                  │   │
│  │  /data/api_keys.json                                            │   │
│  │  [{                                                             │   │
│  │    "id": 4,                                                    │   │
│  │    "merchant_id": 1,                                           │   │
│  │    "key": "sk_test_...",  ← Auto-generated                    │   │
│  │    "label": "Auto-generated from session abc...",             │   │
│  │    "mode": "test",                                             │   │
│  │    "created_at": "2026-02-08..."                              │   │
│  │  }]                                                            │   │
│  │                                                                  │   │
│  │  /data/audit.log                                                │   │
│  │  2026-02-08T15:30:00Z | - | - | WEBHOOK_STRIPE_SUCCESS ...    │   │
│  │  2026-02-08T15:30:01Z | - | - | API_KEY_CREATED ...           │   │
│  │                                                                  │   │
│  └──────────────────────────────────────────────────────────────────┘   │
│                                                                            │
└────────────────────────────────────────────────────────────────────────────┘
                             ↓ (network boundary)
┌────────────────────────────────────────────────────────────────────────────┐
│                         EXTERNAL PAYMENT PROVIDERS                         │
│                                                                            │
│  ┌─────────────────────────────────────┐                                 │
│  │  STRIPE                             │                                 │
│  │                                     │                                 │
│  │  1. Create payment intent via REST  │                                 │
│  │  2. Set metadata.session_id         │                                 │
│  │  3. Customer pays in Stripe UI      │                                 │
│  │  4. Payment succeeds                │                                 │
│  │  5. → POST /webhooks/stripe         │                                 │
│  │     {type: "payment_intent.succeeded",                               │
│  │      data: {object: {metadata: {session_id: "..."}}}               │
│  │  6. ← 200 OK + {success, invoice, api_key_id}                       │
│  │                                     │                                 │
│  └─────────────────────────────────────┘                                 │
│                                                                            │
│  ┌─────────────────────────────────────┐                                 │
│  │  ONE.COM                            │                                 │
│  │                                     │                                 │
│  │  1. Create payment session on One.com                                │
│  │  2. Customer pays                   │                                 │
│  │  3. One.com processes payment       │                                 │
│  │  4. → POST /webhooks/onecom        │                                 │
│  │     {event: "payment.completed",                                    │
│  │      reference: "session_id",                                       │
│  │      amount: 99.99}                                                │
│  │  5. ← 200 OK + {success, invoice, api_key_id}                       │
│  │                                     │                                 │
│  └─────────────────────────────────────┘                                 │
│                                                                            │
│  ┌─────────────────────────────────────┐                                 │
│  │  WEB3 / BLOCKCHAIN                  │                                 │
│  │                                     │                                 │
│  │  1. Customer connects wallet        │                                 │
│  │  2. Initiates blockchain tx         │                                 │
│  │  3. Network confirms (6+ blocks)    │                                 │
│  │  4. → POST /webhooks/web3          │                                 │
│  │     {event: "payment.confirmed",                                    │
│  │      session_id: "...",                                            │
│  │      blockchain_tx_id: "0x..."}                                    │
│  │  5. ← 200 OK + {success, invoice, api_key_id}                       │
│  │                                     │                                 │
│  └─────────────────────────────────────┘                                 │
│                                                                            │
└────────────────────────────────────────────────────────────────────────────┘
```

## State Machine (Detailed)

```
                    ┌─────────────────────────────────────────┐
                    │        INITIAL STATE: "created"        │
                    │    (Session just created, not paid)     │
                    └─────────────────────────────────────────┘
                                    │
                    ┌───────────────┼───────────────┐
                    │               │               │
                    ↓               ↓               ↓
           ┌──────────────┐ ┌──────────────┐ ┌──────────────┐
           │  "pending"   │ │   "paid"     │ │  "failed"    │
           │              │ │              │ │              │
           │ (Optional)   │ │ (Terminal)   │ │ (Terminal)   │
           │              │ │              │ │              │
           │ Payment      │ │ Webhook      │ │ Customer     │
           │ in progress  │ │ confirmed    │ │ cancelled or │
           │              │ │              │ │ error        │
           └──────────────┘ └──────────────┘ └──────────────┘
                    │               │               │
                    └───────────────┴───────────────┘
                          (No return)

Valid Transitions:
  created → pending ✓
  created → paid ✓
  created → failed ✓
  pending → paid ✓
  pending → failed ✓
  
Invalid Transitions (BLOCKED):
  paid → anything ✗
  failed → anything ✗
  pending → created ✗
  (etc)

On Webhook for PAID:
  1. Check: is session in a state that can transition to PAID?
     - created → paid? ✓ ALLOWED
     - pending → paid? ✓ ALLOWED
     - paid → paid? ✗ ALREADY PAID (gracefully handle)
  
  2. If valid: update session atomically
     - status = "paid"
     - payment_status = "completed"
     - paid_at = now()
     - payment_provider = provider
     - provider_id = provider_transaction_id
  
  3. Create invoice + unlock API keys + grant access
```

## Data Flow (Happy Path)

```
1. MERCHANT creates session
   POST /create_session
   Headers: X-API-Key: sk_test_...
   Body: {amount: 99.99, ...}
   ↓
   Response: {session_id: "abc123", url: "https://.../checkout?session=abc123"}
   
2. Session persisted
   sessions.json:
   [{
     "id": "abc123",
     "status": "created",
     "payment_status": "not_started",
     ...
   }]
   
3. CUSTOMER visits checkout
   GET /checkout?session=abc123
   ↓
   Returns: Branded HTML with Stripe/One.com embedded
   
4. CUSTOMER pays
   Clicks "Pay" in hosted form
   ↓
   Payment provider (Stripe/One.com/Web3) processes payment
   
5. PAYMENT PROVIDER sends webhook
   POST /webhooks/stripe
   {
     "type": "payment_intent.succeeded",
     "data": {
       "object": {
         "id": "pi_123",
         "metadata": {"session_id": "abc123"}
       }
     }
   }
   
6. API validates and processes
   ├─ Load session "abc123" from sessions.json
   ├─ Check: status="created" → "paid"? ✓ ALLOWED
   ├─ Mark session.status = "paid"
   ├─ Create invoice in invoices.json
   ├─ Call auto_unlock_api_keys(merchant_id=1)
   │  ├─ Check if merchant already has key
   │  ├─ Generate sk_test_<random>
   │  ├─ Save to api_keys.json
   │  └─ Return {id: 4, key: "sk_test_..."}
   ├─ Call generate_customer_access_link()
   │  ├─ Create JWT token (exp: +7 days)
   │  └─ Return {token: "eyJ...", access_url: "https://..."}
   └─ Save all changes atomically
   
7. API responds to webhook
   {
     "success": true,
     "session_id": "abc123",
     "invoice": {
       "id": "inv_123",
       "merchant_id": 1,
       "amount": 99.99,
       "payment_provider": "stripe"
     },
     "api_key_generated": 4,
     "customer_access": {
       "token": "eyJ...",
       "expires_at": "2026-02-15T...",
       "access_url": "https://api.apiblockchain.io/access/abc123?token=eyJ..."
     }
   }
   
8. Post-Payment
   ├─ Session now marked PAID
   ├─ Merchant can use sk_test_<random> immediately
   ├─ Customer has 7-day access token
   ├─ Invoice stored for accounting
   └─ Everything audit logged

9. MERCHANT checks status (anytime)
   GET /session/{session_id}/status
   ↓
   Response: {status: "paid", payment_provider: "stripe", paid_at: "...", ...}
   
10. CUSTOMER uses access link (next 7 days)
    GET /access/abc123?token=eyJ...
    ↓
    Returns: Invoice + API key + dashboard link
```

---

## Idempotency & Safety

```
Scenario: Webhook retried (network hiccup)

First attempt:
  POST /webhooks/stripe → session "abc123" status="created"
  ├─ Check transition: created → paid? ✓
  ├─ Update: status="paid"
  └─ Respond: 200 OK {success: true, invoice: {...}}

Second attempt (same webhook, retry):
  POST /webhooks/stripe → session "abc123" status="paid"
  ├─ Check transition: paid → paid? ✗ ALREADY PAID
  ├─ Respond: 200 OK {success: true, message: "Already in terminal state: paid"}
  └─ No duplicate invoice, no duplicate key, no double charge

RESULT: ✓ Safe. Idempotent.
```

---

## Error Handling

```
404 Session Not Found
└─ Webhook references session_id that doesn't exist
   └─ Return: 404 + "Session not found"

409 Invalid State Transition
└─ Session already in terminal state (paid/failed)
   └─ Return: 409 + "Invalid state transition"

400 Missing Required Field
└─ Webhook missing session_id
   └─ Return: 400 + "No session_id in webhook"

503 Read-Only Filesystem
└─ Railway persistent volume down
   └─ Return: 503 + "Persistence disabled"

500 Internal Error
└─ JSON parsing error, file write error, etc
   └─ Return: 500 + error message
   └─ Audit logged for investigation
```

---

**Architecture Status: ✅ COMPLETE**

All components implemented, tested, and deployed to production.
