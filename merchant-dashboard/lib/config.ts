// Single source of truth for the backend URL.
// Set NEXT_PUBLIC_API_URL at build time to override (it is inlined into the client bundle).
const PROD_API_URL = 'https://apiblockchain-production-production.up.railway.app';
const DEV_API_URL = 'http://127.0.0.1:8000';

const configured = process.env.NEXT_PUBLIC_API_URL || '';

export const API_BASE = (
  configured.startsWith('http')
    ? configured
    : process.env.NODE_ENV === 'production' ? PROD_API_URL : DEV_API_URL
).replace(/\/+$/, '');

// The auth bypass only ever works in `next dev`; production builds ignore the flag.
export const DEV_BYPASS_AUTH =
  process.env.NODE_ENV !== 'production' && process.env.NEXT_PUBLIC_DEV_BYPASS_AUTH === 'true';
