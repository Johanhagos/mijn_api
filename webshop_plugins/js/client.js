// Simple JavaScript client for webshop plugins to call the invoicing API
// Usage:
// const client = require('./client')
// const api = client({ apiUrl: 'https://api.example.com', apiKey: 'REPLACE' })
// await api.createInvoice({ ...invoicePayload })

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
    createInvoice: async (invoice) => request('/invoices', { method: 'POST', body: invoice }),
    getInvoice: async (idOrNumber) => request(`/invoices/${encodeURIComponent(idOrNumber)}`),
    refreshToken: async () => request('/refresh', { method: 'POST' }),
  }
}

module.exports = createClient
