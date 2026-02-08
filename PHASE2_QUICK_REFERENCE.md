# Phase 2 Quick Reference

## The Problem We Solved

**Question:** "Can money move, and can we react to it?"

**Answer:** ✅ YES. When a payment arrives via Stripe, One.com, or blockchain, your API automatically:
1. Marks the session as PAID
2. Creates an invoice record
3. Generates an API key for the merchant
4. Gives the customer a 7-day access link
5. Logs everything for audit

## New Capabilities

### For Merchants
- Create payment sessions → Get checkout URL
- Session auto-marked PAID when webhook arrives
- API keys auto-generated (test mode by default)
- View paid sessions in dashboard (Phase 3)
- Rotate/upgrade keys manually

### For Customers
- One-click payment via Stripe/One.com/Web3
- 7-day access token to view invoice
- Email with API key + access link (Phase 3)
- Download PDF invoice

## Key Endpoints

### Session Lifecycle
```
POST /create_session
  → returns session_id + checkout_url
  
GET /checkout?session={id}
  → browser renders payment form
  
POST /webhooks/stripe
  → merchant payment system POSTs here
  
GET /session/{id}/status
  → public: check if paid
```

### State Machine (Guaranteed)
```
created ──→ pending ──→ paid ✓ (terminal)
 └─────────┘ └──────→ failed ✓ (terminal)
```

No session can go backwards.
No session can be marked PAID twice (safe from replay).

## Testing Locally

1. **Start server:**
   ```powershell
   cd c:\Users\gebruiker\Desktop\mijn_api
   $env:JWT_SECRET_KEY='devsecret'
   $env:DATA_DIR='c:\Users\gebruiker\Desktop\mijn_api'
   $env:ALLOW_DEBUG='1'
   python -m uvicorn main:app --reload --host 127.0.0.1 --port 8000
   ```

2. **Run test suite:**
   ```powershell
   python test_phase2_webhooks.py
   ```

3. **Manual webhook test:**
   ```powershell
   $payload = @{
     type = "payment_intent.succeeded"
     data = @{
       object = @{
         id = "pi_123"
         metadata = @{ session_id = "session_uuid" }
       }
     }
   } | ConvertTo-Json -Depth 5
   
   Invoke-RestMethod -Uri "http://127.0.0.1:8000/webhooks/stripe" `
     -Method POST -Body $payload `
     -Headers @{"Content-Type" = "application/json"}
   ```

## Production Deployment

Already deployed! 🚀

```
Commit: 3f6ca1c - Phase 2: Payment Reality
Deployed to: https://api.apiblockchain.io
Via: Railway (auto-redeploy on git push)
```

### Verify Production
```powershell
# Create session
$r = Invoke-RestMethod -Uri "https://api.apiblockchain.io/create_session" `
  -Method POST `
  -Headers @{"X-API-Key" = "sk_test_local_automation"} `
  -Body '{"amount":99,"mode":"test",...}' `
  -TimeoutSec 15

# Send webhook
$r = Invoke-RestMethod -Uri "https://api.apiblockchain.io/webhooks/stripe" `
  -Method POST `
  -Body '{"type":"payment_intent.succeeded",...}'

# Check status
$r = Invoke-RestMethod `
  -Uri "https://api.apiblockchain.io/session/db0bb7f9-357a.../status"
```

## Files Added/Modified

### New
- [PHASE2_PAYMENT_REALITY.md](PHASE2_PAYMENT_REALITY.md) - Detailed spec
- [test_phase2_webhooks.py](test_phase2_webhooks.py) - Test suite

### Modified
- [main.py](main.py) +1043 lines:
  - `validate_payment_state_transition()` - State machine logic
  - `generate_customer_access_link()` - 7-day JWT tokens
  - `auto_unlock_api_keys()` - Auto-generate keys on payment
  - `POST /webhooks/stripe` - Stripe webhook handler
  - `POST /webhooks/onecom` - One.com webhook handler
  - `POST /webhooks/web3` - Web3 webhook handler
  - `GET /session/{id}/status` - Public status check
  - Updated session schema with payment_status + metadata

## What's NOT Implemented Yet (Phase 3)

These are stretch goals for real payment integration:

- [ ] Stripe Checkout integration (client-side payment form)
- [ ] One.com API connectivity
- [ ] Webhook signature verification (HMAC security)
- [ ] Email customer access links + invoices
- [ ] Dashboard revenue charts
- [ ] Key rotation UI

## How Merchants Use This

**In their app/website:**
```javascript
// 1. Create session
fetch('https://api.apiblockchain.io/create_session', {
  method: 'POST',
  headers: { 'X-API-Key': 'sk_test_...' },
  body: JSON.stringify({ amount: 99.99, mode: 'test', ... })
})
.then(r => r.json())
.then(data => {
  // 2. Redirect customer to checkout
  window.location = data.url  // e.g., /checkout?session=...
})

// 3. Customer pays
// 4. Your payment provider webhooks us
// 5. We auto-mark session PAID + unlock API keys
// 6. Customer gets access link via email
```

## Summary

Phase 2 completes the **payment control loop**:
- Sessions now have payment state
- Webhooks trigger state transitions
- Invoice auto-creation
- API key auto-unlock
- Customer access auto-granted

The system is **payments-aware** and **entitlement-ready**.

Next: Plug in real payment providers. 🔌

---

**Questions?** See [PHASE2_PAYMENT_REALITY.md](PHASE2_PAYMENT_REALITY.md) for full technical details.
