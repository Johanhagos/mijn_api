export const api = async (path, method = 'GET', data) => {
  const token = typeof window !== 'undefined' ? localStorage.getItem('jwt') : null;
  const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}${path}`, {
    method,
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { 'Authorization': `Bearer ${token}` } : {}),
    },
    body: data ? JSON.stringify(data) : undefined,
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
};
