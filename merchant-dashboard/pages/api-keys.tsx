import { useEffect, useState } from 'react';
import { api } from '../lib/api';

export default function ApiKeys() {
  const [keys, setKeys] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [creating, setCreating] = useState(false);
  const [lastCreated, setLastCreated] = useState<string | null>(null);

  const fetchKeys = async () => {
    try {
      setLoading(true);
      const data = await api('/merchant/api-keys');
      setKeys(data || []);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchKeys();
  }, []);

  const revokeKey = async (id: string) => {
    await api(`/merchant/api-keys/${id}/revoke`, 'POST');
    fetchKeys();
  };

  const createKey = async () => {
    try {
      setCreating(true);
      const newKey = await api('/merchant/api-keys', 'POST');
      // Backend should return the plaintext key once on creation
      setLastCreated(newKey.key || newKey);
      fetchKeys();
      if (typeof window !== 'undefined' && newKey.key) {
        try { await navigator.clipboard.writeText(newKey.key); } catch {}
      }
    } catch (err) {
      console.error(err);
      alert('Failed to create key: ' + err);
    } finally {
      setCreating(false);
    }
  };

  return (
    <div className="p-8">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-3xl font-bold">API Keys</h1>
        <div>
          <button
            onClick={createKey}
            disabled={creating}
            className="bg-green-600 text-white px-4 py-2 rounded hover:bg-green-700 disabled:opacity-60"
          >
            {creating ? 'Creating…' : 'Create API Key'}
          </button>
        </div>
      </div>

      {lastCreated && (
        <div className="mb-4 p-4 border rounded bg-yellow-50">
          <p className="font-medium">New key created — copied to clipboard:</p>
          <pre className="bg-white p-2 mt-2 rounded text-sm">{lastCreated}</pre>
        </div>
      )}

      {loading ? <p>Loading...</p> : (
        <ul className="space-y-4">
          {keys.map(k => (
            <li key={k.id} className="border p-4 rounded flex justify-between items-center">
              <div>
                <div className="font-mono text-sm">{k.key}</div>
                <div className="text-xs text-gray-500">Created: {new Date(k.created_at || k.createdAt || 0).toLocaleString()}</div>
              </div>
              <div className="flex items-center gap-2">
                <button
                  onClick={() => { navigator.clipboard?.writeText(k.key); }}
                  className="bg-blue-600 text-white px-3 py-1 rounded hover:bg-blue-700"
                >
                  Copy
                </button>
                <button
                  onClick={() => revokeKey(k.id)}
                  className="bg-red-600 text-white px-3 py-1 rounded hover:bg-red-700"
                >
                  Revoke
                </button>
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
