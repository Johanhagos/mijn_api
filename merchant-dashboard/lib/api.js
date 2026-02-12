const API_BASE_RAW = process.env.NEXT_PUBLIC_API_URL || '';
const API_BASE = API_BASE_RAW.startsWith('http') ? API_BASE_RAW : 'https://api.apiblockchain.io';

export const api = async (path, method = 'GET', data) => {
  const token = typeof window !== 'undefined' ? localStorage.getItem('jwt') : null;
  const url = `${API_BASE}${path}`;
  const res = await fetch(url, {
    method,
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { 'Authorization': `Bearer ${token}` } : {}),
    },
    body: data ? JSON.stringify(data) : undefined,
    credentials: 'include',
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
};

export const login = async (name, password) => {
  const res = await fetch(`${API_BASE}/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ name, password }),
    credentials: 'include',
  });
  if (!res.ok) throw new Error(await res.text());
  const json = await res.json();
  if (typeof window !== 'undefined' && json?.access_token) {
    localStorage.setItem('jwt', json.access_token);
    if (json?.merchant_id) localStorage.setItem('merchant_id', String(json.merchant_id));
    if (json?.merchant_name || json?.merchant) localStorage.setItem('merchant_name', String(json.merchant_name || json.merchant));
    if (json?.email) localStorage.setItem('merchant_email', String(json.email));
  }
  return json;
};

export const protectedApi = async (path, method = 'GET', data) => {
  const token = typeof window !== 'undefined' ? localStorage.getItem('jwt') : null;
  const url = `${API_BASE}${path}`;

  const doRequest = async (bearer) => {
    const headers = { 'Content-Type': 'application/json' };
    if (bearer) headers['Authorization'] = `Bearer ${bearer}`;
    return fetch(url, {
      method,
      headers,
      body: data ? JSON.stringify(data) : undefined,
      credentials: 'include',
    });
  };

  let res = await doRequest(token || undefined);
  if (res.status === 401) {
    const r = await fetch(`${API_BASE}/refresh`, { method: 'POST', credentials: 'include' });
    if (r.ok) {
      const j = await r.json();
      const newToken = j?.access_token || j?.token;
      if (newToken && typeof window !== 'undefined') {
        localStorage.setItem('jwt', newToken);
        res = await doRequest(newToken);
      }
    }
  }

  if (res.status === 401) {
    if (typeof window !== 'undefined') {
      localStorage.removeItem('jwt');
      localStorage.removeItem('merchant_id');
      localStorage.removeItem('merchant_name');
      localStorage.removeItem('merchant_email');
      window.location.href = '/login';
    }
    throw new Error('Unauthorized');
  }

  if (!res.ok) throw new Error(await res.text());
  return res.json();
};

const defaultApi = { api, login, protectedApi };
export default defaultApi;
