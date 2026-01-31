import { useEffect, useState } from 'react';
import { api } from '../lib/api';

export default function PluginSetup() {
  const [key, setKey] = useState('');
  const [showKey, setShowKey] = useState(false);
  const [creating, setCreating] = useState(false);

  const loadKey = async () => {
    try {
      const keys = await api('/merchant/api-keys');
      setKey(keys?.[0]?.key || '');
    } catch (err) {
      console.error(err);
    }
  };

  useEffect(() => { loadKey(); }, []);

  const createKey = async () => {
    try {
      setCreating(true);
      const newKey = await api('/merchant/api-keys', 'POST');
      setKey(newKey.key || newKey);
      try { await navigator.clipboard.writeText(newKey.key || newKey); } catch {}
    } catch (err) {
      console.error(err);
      alert('Failed to create key: ' + err);
    } finally {
      setCreating(false);
    }
  };

  const snippet = (k: string) => ` <script src="https://cdn.apiblockchain.io/plugin.min.js"></script>\n<script>\n  ApiBlockchain.init({\n    apiKey: "${k}",\n    mode: "live"\n  });\n</script>`;

  return (
    <div className="p-8">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-3xl font-bold">Plugin Setup</h1>
        <div className="flex gap-2">
          {!key && (
            <button onClick={createKey} disabled={creating} className="bg-green-600 text-white px-3 py-1 rounded">
              {creating ? 'Creating…' : 'Create API Key'}
            </button>
          )}
          {key && (
            <button onClick={() => { navigator.clipboard?.writeText(snippet(key)); }} className="bg-blue-600 text-white px-3 py-1 rounded">
              Copy snippet
            </button>
          )}
        </div>
      </div>

      <p>Copy the snippet below to integrate the plugin:</p>

      <div className="mt-4">
        <div className="mb-2 flex items-center gap-2">
          <label className="text-sm">Show key</label>
          <input type="checkbox" checked={showKey} onChange={e => setShowKey(e.target.checked)} />
        </div>

        <pre className="bg-gray-100 p-4 rounded text-sm">
{showKey ? key || 'No key available' : '••••••••••••••••••'}
        </pre>

        <pre className="bg-gray-50 p-4 mt-4 rounded text-sm">
{snippet(key || '')}
        </pre>
      </div>
    </div>
  );
}
