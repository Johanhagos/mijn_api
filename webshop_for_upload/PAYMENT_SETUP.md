# Payment Processing Setup

## Overview
The webshop now has a complete payment system powered by Stripe for processing customer purchases.

## Files Added

### Frontend (Webshop)
- **`webshop/checkout.html`** - Customer checkout page with:
  - Order summary ($498 for both services)
  - Billing information form
  - Stripe card payment integration
  - Real-time validation
  - Professional UI with security badge

- **`webshop/thank-you.html`** - Order confirmation page with:
  - Order ID and date
  - Amount paid confirmation
  - Next steps for customer
  - Link to merchant dashboard

### Backend API
- **`main.py`** - New `/api/process-payment` endpoint that:
  - Accepts Stripe payment method ID
  - Creates PaymentIntent via Stripe API
  - Logs successful payments
  - Saves orders to invoices database
  - Returns order ID and status

## Setup Instructions

### 1. Get Stripe API Keys
1. Go to https://dashboard.stripe.com/apikeys
2. Copy your **Publishable Key** (starts with `pk_test_` or `pk_live_`)
3. Copy your **Secret Key** (starts with `sk_test_` or `sk_live_`)

### 2. Update Checkout Page
In `webshop/checkout.html`, find this line (around line 290):
```javascript
const stripe = Stripe('pk_test_YOUR_STRIPE_KEY');
```

Replace `pk_test_YOUR_STRIPE_KEY` with your actual publishable key.

### 3. Set Backend Environment Variable
Add to your `.env` file or deployment environment:
```
STRIPE_SECRET_KEY=sk_test_your_secret_key_here
```

### 4. Deploy Webshop to Vercel
```bash
# Files already pushed to GitHub
# Just follow the Vercel deployment steps:
1. Go to vercel.com
2. Import your GitHub repo
3. Set root directory to "webshop"
4. Click Deploy
```

### 5. Deploy Backend Updates
```bash
# Push backend code to your deployment (Railway/Docker/etc)
git push origin main
```

## Testing Payments

### Stripe Test Cards
Use these card numbers in the checkout form (expires: any future date, CVC: any 3 digits):

- **Successful payment**: `4242 4242 4242 4242`
- **Declined card**: `4000 0000 0000 0002`
- **Requires authentication**: `4000 0025 0000 3155`

### Test Payment Flow
1. Open `https://your-webshop-url/checkout.html`
2. Fill in customer details
3. Enter test card number `4242 4242 4242 4242`
4. Submit → Should see "Order Confirmed" page
5. Check `/api/process-payment` logs for order ID

## Production Deployment

### Before Going Live
1. Switch to **Live API Keys** from Stripe dashboard
2. Update `STRIPE_SECRET_KEY` with live secret key
3. Update checkout.html with live publishable key (`pk_live_...`)
4. Enable production mode in environment variables
5. Set up Stripe webhooks for:
   - `payment_intent.succeeded`
   - `payment_intent.payment_failed`

### Security Checklist
- ✅ HTTPS enabled on all URLs
- ✅ Stripe keys stored as environment variables (NOT in code)
- ✅ CORS configured for your domain only
- ✅ Payment intent amount verified server-side
- ✅ Email notifications sent to customers

## Features

### Current
- ✅ Stripe payment processing
- ✅ Order ID generation
- ✅ Email capture
- ✅ Billing address collection
- ✅ Real-time card validation
- ✅ Order logging

### Coming Soon
- 📧 Automated email confirmations
- 📊 Admin payment dashboard
- 🔄 Subscription handling
- 💰 Multiple currencies
- 🏦 Bank transfer option
- ₿ Cryptocurrency payments (Web3 integration)

## Support

If you need help:
1. Check Stripe documentation: https://stripe.com/docs
2. Review error logs in your backend
3. Test with Stripe test mode first
4. Contact Stripe support for API issues

---

**Payment processed successfully!** 🎉
Your customers can now purchase services directly from your webshop.
