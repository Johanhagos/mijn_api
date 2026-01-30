# UX Flow: Mijn API — Invoice & Auth

This document contains the UX flows the frontend team can use to design screens and interactions.

## 1 — Login

- Screen: Login form (email/username + password)
- POST /login → on success store access token (and server sets refresh cookie)
- Redirect to Dashboard

## 2 — Dashboard

- Shows recent invoices and actions: Create invoice, View invoices, Upload logo, Payments

## 3 — Create Invoice

1. Seller info (logo upload optional)
2. Buyer info (B2B toggle shows VAT number)
3. Line items (qty, description, unit price, VAT rate)
4. Payment type: Web2 or Web3
   - Web2: select provider (card/bank)
   - Web3: provide tx hash / wallet connect
5. Preview PDF (client-side preview optional)
6. Submit → saves invoice, returns pdf_url and invoice metadata

## 4 — Invoice List / Detail

- List: filter by date / payment type / buyer / status
- Detail: show invoice fields, download PDF, payment status, blockchain link when available

## 5 — Admin

- Manage users
- View audit logs
- Trigger migrations / health

---

Notes for designers:
- Keep the PDF layout simple and mirror the API PDF fields.
- Web3 fields should be visually distinct and include an external explorer link when tx hash is present.
