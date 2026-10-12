/**
 * APIBlockchain API Configuration
 * This file contains the API endpoint configuration for the webshop
 */

const API_CONFIG = {
  // Main API endpoint for invoicing, checkout, and other services.
  // Prefer the local FastAPI backend during development and Railway only in production.
  baseURL: (typeof window !== 'undefined' && window.location.hostname === 'localhost')
    ? 'http://127.0.0.1:8000'
    : 'https://apiblockchain-production-production.up.railway.app',
  
  // Endpoints
  endpoints: {
    checkout: '/checkout',
    invoices: '/invoices',
    createInvoice: '/invoices',
    getInvoice: (id) => `/invoices/${id}`,
    sessions: '/sessions',
    createSession: '/checkout',
    health: '/health'
  },
  
  // Helper function to build full URLs
  getURL: (endpoint) => {
    return API_CONFIG.baseURL + endpoint;
  },
  
  // Fetch helper with error handling
  async fetch(endpoint, options = {}) {
    const url = API_CONFIG.getURL(endpoint);
    
    try {
      const response = await fetch(url, {
        ...options,
        headers: {
          'Content-Type': 'application/json',
          ...options.headers
        }
      });
      
      if (!response.ok) {
        throw new Error(`API Error: ${response.statusText} (${response.status})`);
      }
      
      return await response.json();
    } catch (error) {
      console.error('API Request Error:', error);
      throw error;
    }
  }
};

// Export for use in other scripts
if (typeof module !== 'undefined' && module.exports) {
  module.exports = API_CONFIG;
}
