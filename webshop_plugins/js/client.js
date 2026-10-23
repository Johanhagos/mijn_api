// Server-side JavaScript client for connecting a webshop to APIBlockchain.
// Keep the API key on the server; never ship it to the browser.
// Usage:
// const client = require('./client')
// const api = client({ apiUrl: 'https://apiblockchain-production-production.up.railway.app', apiKey: process.env.APIBLOCKCHAIN_KEY })
// const session = await api.createSession({ amount: 12.5, order_id: '1042', success_url, cancel_url })
// redirect the customer to session.url, later: (await api.getSessionStatus(session.id)).status === 'paid'

const fetch = require('node-fetch')

function createClient({ apiUrl, apiKey, timeout = 10000 }) {
  if (!apiUrl) throw new Error('apiUrl required')
  if (!apiKey) throw new Error('apiKey required')

  async function request(path, opts = {}) {
    const url = apiUrl.replace(/\/$/, '') + path
    const res = await fetch(url, {
      method: opts.method || 'GET',
      headers: Object.assign({
        'Content-Type': 'application/json',
        'X-API-Key': apiKey
      }, opts.headers || {}),
      body: opts.body ? JSON.stringify(opts.body) : undefined,
      timeout
    })

    const text = await res.text()
    let data = null
    try { data = JSON.parse(text) } catch (e) { data = text }
    if (!res.ok) {
      const err = new Error('API error')
      err.status = res.status
      err.body = data
      throw err
    }
    return data
  }

  return {
    // Hosted APIUSD checkout for an order; send the customer to the returned `url`
    createSession: async (session) => request('/create_session', { method: 'POST', body: session }),
    // `status` is 'paid' once the APIUSD payment is verified on-chain
    getSessionStatus: async (id) => request(`/session/${encodeURIComponent(id)}/status`),
    createInvoice: async (invoice) => request('/invoices', { method: 'POST', body: invoice }),
    getInvoice: async (id) => request(`/invoices/${encodeURIComponent(id)}`),
  }
}

module.exports = createClient
