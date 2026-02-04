(function () {
  const ApiBlockchain = {
    init(config = {}) {
      this.apiKey = config.apiKey || null
      this.mode = config.mode || "test"
      // Default to local API for developer convenience
      this.apiUrl = config.apiUrl || "http://localhost:8000"
      // Hosted checkout base (local by default for dev)
      this.hostedUrl = config.hostedUrl || "http://localhost:8000"
    },

    async createSessionRemote({ amount, success_url, cancel_url }) {
      // Try to create a server-side session (preferred). Requires merchant to provide
      // an apiUrl + apiKey in the init config (merchant may do this from a secure server).
      if (!this.apiUrl || !this.apiKey) return null

      try {
        const res = await fetch(this.apiUrl.replace(/\/$/, "") + "/create_session", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "X-API-Key": this.apiKey
          },
          body: JSON.stringify({ amount, mode: this.mode, success_url, cancel_url })
        })
        if (!res.ok) return null
        return await res.json()
      } catch (e) {
        return null
      }
    },

    openHostedCheckoutUrl(url) {
      const w = window.open(url, "apiblockchain_checkout", "width=500,height=800")
      if (!w) {
        // popup blocked — fallback to redirect
        window.location.href = url
      }
      return w
    },

    async checkout({ amount, success_url, cancel_url } = {}) {
      // Build success/cancel defaults to close window and optionally reload opener
      const defaultSuccess = window.location.href
      success_url = success_url || defaultSuccess
      cancel_url = cancel_url || defaultSuccess

      // 1) Preferred: ask merchant backend to create a server-side session
      const session = await this.createSessionRemote({ amount, success_url, cancel_url })
      if (session && session.url) {
        this.openHostedCheckoutUrl(session.url)
        return { session }
      }

      // 2) Fallback: open hosted checkout with query params
      const params = new URLSearchParams({ amount: String(amount), mode: this.mode, success_url, cancel_url })
      // If merchant provided an apiKey in init, include it (merchant knowingly exposes it)
      if (this.apiKey) params.set("api_key", this.apiKey)
      const url = this.hostedUrl.replace(/\/$/, "") + "/checkout?" + params.toString()
      this.openHostedCheckoutUrl(url)
      return { url }
    }
  }

  window.ApiBlockchain = ApiBlockchain
})()
