Webshop plugins

Connect a webshop to APIBlockchain so customers pay their order in APIUSD. You need an
APIBlockchain account with an active plan and an API key (Dashboard > API Keys).

How a payment works
1. The shop creates a checkout session: `POST /create_session` with header `X-API-Key`.
2. The customer is sent to the session `url` (hosted checkout) and pays in APIUSD.
3. APIBlockchain marks the session paid only after verifying the transfer on-chain.
4. The shop checks `GET /session/{id}/status` (`"status": "paid"`) and completes the order.
   After paying, the customer is sent back to the session's `success_url`.

WooCommerce
- `woocommerce/apiblockchain-apiusd/` - payment method "Pay with APIUSD".
- Install: WordPress > Plugins > Add New > Upload Plugin, choose `apiblockchain-apiusd.zip`
  (download it from the dashboard, Plugin Setup page). Then WooCommerce > Settings >
  Payments > APIBlockchain (APIUSD): enable it and paste your live API key.
- The shop currency must be EUR (APIUSD is charged 1:1 against the order total).
- Orders are completed on the thank-you page, and every 5 minutes for customers who closed
  the tab after paying.
- After changing the PHP file, rebuild the zip in `merchant-dashboard/public/downloads/`
  (the zip contains the `apiblockchain-apiusd/` folder).

Other shops (Node.js)
- `js/client.js`: `const api = require('./client')({ apiUrl, apiKey })`, then
  `api.createSession({...})` and `api.getSessionStatus(id)`.

create_session fields
- `amount` (required, EUR), `success_url`, `cancel_url`, `order_id`, `description`,
  `customer_name`, `customer_email`, `buyer_country`, `buyer_address`, `buyer_vat_number`,
  `items`: `[{ "name", "quantity", "unit_price" }]` (used as invoice lines when they add up to `amount`).

Security
- Keep the API key on the server; never put it in browser JavaScript.
- Use HTTPS. Rotate keys in the dashboard; revoking a key stops it immediately.
