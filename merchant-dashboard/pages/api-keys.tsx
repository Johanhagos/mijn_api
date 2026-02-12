import { useEffect, useState } from 'react';
import dynamic from 'next/dynamic';
import api from '../lib/api';
import AuthGuard from '../components/AuthGuard';
import Toast from '../components/Toast';

function ApiKeys() {
  const [keys, setKeys] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [creating, setCreating] = useState(false);
  const [lastCreated, setLastCreated] = useState<string | null>(null);
  const [showModal, setShowModal] = useState(false);
  const [copiedId, setCopiedId] = useState<number | null>(null);

  const fetchKeys = async () => {
    try {
      setLoading(true);
      const data = await api.protectedApi('/api-keys');
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
    await api.protectedApi(`/api-keys/${id}`, 'DELETE');
    fetchKeys();
  };

  const [mode, setMode] = useState<'live' | 'test'>('live');

  const createKey = async () => {
      try {
        setCreating(true);
        const newKey = await api.protectedApi('/api-keys', 'POST', { mode, label: `${mode}-key` });
      // Backend returns plaintext key once at creation time
      const raw = newKey.key || newKey;
      setLastCreated(raw);
      setShowModal(true);
      // show toast confirming copy
      setTimeout(() => setCopiedId(null), 1500);
      setShowToast(true);
      fetchKeys();
      if (typeof window !== 'undefined' && raw) {
        try { await navigator.clipboard.writeText(raw); setCopiedId(-1); setTimeout(()=>setCopiedId(null),1500); } catch {}
      }
    } catch (err) {
      console.error(err);
      alert('Failed to create key: ' + err);
    } finally {
      setCreating(false);
    }
  };

  const [showToast, setShowToast] = useState(false);

  return (
    <AuthGuard>
      <div className="p-8">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-3xl font-bold">API Keys</h1>
        <div>
          <div className="flex items-center gap-3">
            <div className="flex items-center gap-2">
              <label className="text-sm">Mode</label>
              <select value={mode} onChange={e => setMode(e.target.value as any)} className="border rounded p-1">
                <option value="live">Live</option>
                <option value="test">Test</option>
              </select>
            </div>
            <button
              onClick={createKey}
              disabled={creating}
              className="bg-green-600 text-white px-4 py-2 rounded hover:bg-green-700 disabled:opacity-60"
            >
              {creating ? 'Creating…' : 'Create API Key'}
            </button>
          </div>
        </div>
      </div>

      {showModal && lastCreated && (
        <div className="mb-4 p-4 border rounded bg-yellow-50">
          <p className="font-medium">New key created — copied to clipboard:</p>
          <div className="flex items-start gap-4 mt-2">
            <pre className="bg-white p-2 rounded text-sm break-all">{lastCreated}</pre>
            <div className="flex flex-col gap-2">
              <button onClick={async () => { try { await navigator.clipboard.writeText(lastCreated); setCopiedId(-1); setTimeout(()=>setCopiedId(null),1500);} catch{} }} className="bg-green-600 text-white px-3 py-1 rounded">{copiedId===-1 ? 'Copied!' : 'Copy'}</button>
              <button onClick={() => { setShowModal(false); setLastCreated(null); }} className="bg-gray-300 text-gray-800 px-3 py-1 rounded">Close</button>
            </div>
          </div>
        </div>
      )}

      <Toast open={showToast} message={lastCreated ? 'API key created and copied to clipboard' : 'API key created'} />

      {loading ? <p>Loading...</p> : (
        <ul className="space-y-4">
          {keys.map(k => (
            <li key={k.id} className="card flex justify-between items-center">
              <div>
                <div className="font-medium">{k.label || `Key ${k.id}`}</div>
                <div className="text-xs text-gray-500">Created: {new Date(k.created_at || k.createdAt || 0).toLocaleString()}</div>
              </div>
              <div className="flex items-center gap-2">
                <span className={`badge ${((k.mode||'live')==='live')? 'badge-live' : 'badge-test'}`}>{(k.mode||'live').toUpperCase()}</span>
                <button
                  onClick={async () => {
                    alert('Raw key material is only shown at creation time for security. Create a new key to receive the raw value.');
                  }}
                  className="bg-green-600 text-white px-3 py-1 rounded hover:bg-green-700"
                >
                  Copy
                </button>
                <button
                  onClick={async () => { if(confirm('Revoke this key?')) { await revokeKey(k.id); setCopiedId(null); } }}
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
    </AuthGuard>
  );
}

export default dynamic(() => Promise.resolve(ApiKeys), { ssr: false });
