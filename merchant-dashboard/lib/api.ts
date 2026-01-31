const API_BASE = process.env.NEXT_PUBLIC_API_URL || '';

export const api = async (path: string, method = 'GET', data?: any) => {
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

export const login = async (name: string, password: string) => {
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
  }
  return json;
};

export const protectedApi = async (path: string, method = 'GET', data?: any) => {
  const token = typeof window !== 'undefined' ? localStorage.getItem('jwt') : null;
  const url = `${API_BASE}${path}`;

  const doRequest = async (bearer?: string) => {
    const headers: any = { 'Content-Type': 'application/json' };
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
    // Try refresh token endpoint (refresh cookie is HttpOnly)
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
      window.location.href = '/login';
    }
    throw new Error('Unauthorized');
  }

  if (!res.ok) throw new Error(await res.text());
  return res.json();
};
