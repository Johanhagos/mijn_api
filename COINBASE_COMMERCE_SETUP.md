# Coinbase Commerce Integration Setup

## Overview
The API now supports cryptocurrency payments via Coinbase Commerce, allowing customers to pay with Bitcoin, Ethereum, and other cryptocurrencies.

## Configuration

### Environment Variables (Backend)
Set these in your Railway environment:

```bash
COINBASE_COMMERCE_API_KEY=837cb701-982d-435a-8abd-724b723a3883
COINBASE_WEBHOOK_SECRET=<your-webhook-secret>
```

### Webhook Setup in Coinbase Commerce Dashboard

1. Log in to [Coinbase Commerce Dashboard](https://commerce.coinbase.com/)
2. Go to Settings → Webhook subscriptions
3. Add webhook endpoint: `https://api.apiblockchain.io/webhooks/coinbase`
4. Select event: `charge:confirmed`
5. Copy the webhook shared secret
6. Set `COINBASE_WEBHOOK_SECRET` environment variable in Railway

## How It Works

### Payment Flow
1. Customer clicks "Generate Crypto Invoice" on checkout page
2. Frontend calls `POST /api/coinbase/create-charge` with:
   - `session_id`: Unique session identifier
   - `amount`: Payment amount in EUR
   - `currency`: "EUR" 
   - `name`: Product name
   - `description`: Product description

3. Backend creates Coinbase Commerce charge and returns:
   - `hosted_url`: Coinbase hosted checkout page
   - `charge_id`: Unique charge identifier
   - `expires_at`: Charge expiration time

4. Customer is redirected to Coinbase Commerce checkout
5. Customer completes payment with crypto
6. Coinbase sends webhook to `/webhooks/coinbase`
7. Backend marks session as paid and creates invoice
8. Customer is redirected to success page

### Webhook Events
- `charge:confirmed` → Session marked as paid, invoice created
- `charge:failed` → Ignored (payment failed)
- `charge:pending` → Ignored (waiting for confirmations)

## Testing

### Local Testing
```bash
# Run test script
python test_coinbase_charge.py
```

### Production Testing
1. Go to checkout page: https://apiblockchain.io/checkout.html?plan=Starter&price=20
2. Select "Cryptocurrency" tab
3. Enter wallet address (any valid address for receipt)
4. Click "Generate Crypto Invoice"
5. You'll be redirected to Coinbase Commerce checkout
6. Complete payment with test crypto (if sandbox) or real crypto (if live)
7. After payment confirmation, webhook triggers and session is marked paid

## Invoice Data Structure
When a crypto payment is confirmed, the invoice includes:
```json
{
  "payment_provider": "coinbase",
  "coinbase_charge_id": "...",
  "crypto_amount": "0.00123",
  "crypto_currency": "BTC",
  "transaction_id": "0x..."
}
```

## Supported Cryptocurrencies
Coinbase Commerce automatically supports:
- Bitcoin (BTC)
- Bitcoin Cash (BCH)
- Ethereum (ETH)
- Litecoin (LTC)
- Dogecoin (DOGE)
- USD Coin (USDC)
- DAI

Customer can choose any of these at checkout.

## Security Notes
- Webhook signature verification is enforced when `COINBASE_WEBHOOK_SECRET` is set
- Only `charge:confirmed` events update session status
- Double-payment protection: sessions in terminal state (paid/failed) cannot be updated
- Session IDs are unique and validated before processing

## Troubleshooting

### Charge Creation Fails
- Check `COINBASE_COMMERCE_API_KEY` is set correctly in Railway
- Verify API key has not been revoked in Coinbase dashboard
- Check backend logs for detailed error messages

### Webhook Not Firing
- Verify webhook URL is correct: `https://api.apiblockchain.io/webhooks/coinbase`
- Check `COINBASE_WEBHOOK_SECRET` is set in Railway
- Ensure Railway service is running and accessible
- Check webhook logs in Coinbase Commerce dashboard

### Invalid Signature Error
- Webhook secret mismatch - verify it matches Coinbase dashboard
- Body encoding issue - webhook expects raw body for signature verification

## Support
- Coinbase Commerce API Docs: https://commerce.coinbase.com/docs/
- Issues: Check Railway logs for detailed error messages
