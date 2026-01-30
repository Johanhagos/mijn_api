Webshop plugin examples

This folder contains example plugins/clients for connecting webshops to the Mijn Invoicing API.

JS client
- `js/client.js` - a small Node.js client to call the API. Install `node-fetch` and use it in server-side webshop code.

WooCommerce example
- `woocommerce/mijn-invoicing-plugin.php` - a minimal WooCommerce plugin that sends completed orders to the API.

How to use
1. Configure API endpoint and API key in the example files (or store in your platform's settings).
2. For WooCommerce, install the PHP file as a plugin and set constants to real values.
3. For Node.js, `const api = require('./client')({ apiUrl, apiKey })` and call `api.createInvoice(payload)`.

Security
- Use HTTPS.
- Use the shop-scoped API key, and rotate regularly.
- Implement server-side validation of payloads before sending.

Customization
- Map your webshop tax lines to the `vat_rate` field.
- Attach order metadata (order_id, customer reference) into the invoice payload.
