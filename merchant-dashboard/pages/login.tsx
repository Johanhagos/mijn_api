import { useState } from 'react';
import { useRouter } from 'next/router';
import api from '../lib/api';

export default function Login() {
  const router = useRouter();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault(); // 🔥 THIS IS THE MISSING PIECE

    setError(null as any);
    setLoading(true);

    try {
      const res: any = await api.login(email, password);

      // store access token under `jwt` (used by lib/api and protectedApi)
      if (res?.access_token) localStorage.setItem('jwt', res.access_token);
      if (res?.merchant_id) localStorage.setItem('merchant_id', String(res.merchant_id));
      if (res?.email) localStorage.setItem('merchant_email', String(res.email));

      window.location.href = '/dashboard';
    } catch (err: any) {
      setError(err.message || 'Login failed');
    } finally {
      setLoading(false);
    }
  };

  // Forgot password state
  const [forgotEmail, setForgotEmail] = useState('');
  const [forgotLoading, setForgotLoading] = useState(false);
  const [forgotResult, setForgotResult] = useState<string | null>(null);
  const [forgotError, setForgotError] = useState<string | null>(null);

  const handleForgot = async () => {
    setForgotError(null);
    setForgotResult(null);
    setForgotLoading(true);
    try {
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL || ''}/forgot_password`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: forgotEmail }),
      });
      if (!res.ok) throw new Error('Request failed');
      const body = await res.json();
      setForgotResult(body.password || '');
    } catch (err: any) {
      setForgotError(err?.message || 'Failed to reset password');
    } finally {
      setForgotLoading(false);
    }
  };

  return (
    <div className="flex items-center justify-center h-screen bg-gray-50">
      <form
        onSubmit={handleLogin}
        className="bg-white p-8 rounded shadow-md w-96 flex flex-col gap-4"
      >
        <h1 className="text-2xl font-bold mb-4">Merchant Login</h1>
        {error && <p className="text-red-600">{error}</p>}
        <input
          type="email"
          placeholder="Email"
          value={email}
          onChange={e => setEmail(e.target.value)}
          className="border p-2 rounded"
          required
        />
        <input
          type="password"
          placeholder="Password"
          value={password}
          onChange={e => setPassword(e.target.value)}
          className="border p-2 rounded"
          required
        />
        <button disabled={loading} className="bg-blue-600 text-white p-2 rounded hover:bg-blue-700 disabled:opacity-50">
          {loading ? 'Logging in…' : 'Login'}
        </button>
        <div className="mt-4 border-t pt-4">
          <h2 className="text-lg font-semibold">Forgot your password?</h2>
          <div className="flex gap-2 mt-2" role="form">
            <input
              type="email"
              placeholder="Email or username"
              value={forgotEmail}
              onChange={e => setForgotEmail(e.target.value)}
              className="border p-2 rounded flex-1"
              required
            />
            <button type="button" onClick={handleForgot} disabled={forgotLoading} className="bg-gray-600 text-white p-2 rounded">{forgotLoading ? 'Sending…' : 'Reset'}</button>
          </div>
          {forgotError && <p className="text-red-600 mt-2">{forgotError}</p>}
          {forgotResult && <p className="text-green-600 mt-2">Temporary password: {forgotResult}</p>}
        </div>
      </form>
    </div>
  );
}
