import { useEffect, useState } from 'react';
import dynamic from 'next/dynamic';
import api from '../lib/api';
import AuthGuard from '../components/AuthGuard';
import Toast from '../components/Toast';

function PluginSetup() {
  const [key, setKey] = useState('');
  const [showKey, setShowKey] = useState(false);
  const [creating, setCreating] = useState(false);
  const [showModal, setShowModal] = useState(false);
  const [copied, setCopied] = useState(false);
  const [snippetMode, setSnippetMode] = useState<'live'|'test'>('live');
  const [showToast, setShowToast] = useState(false);

  const loadKey = async () => {
    try {
      const keys = await api.protectedApi('/api-keys');
      // Prefer live key if present; listing does not include raw key material
      const live = keys?.find((k: any) => (k.mode || 'live') === 'live');
      setKey('');
    } catch (err) {
      console.error(err);
    }
  };

  useEffect(() => { loadKey(); }, []);

  const createKey = async () => {
    try {
      setCreating(true);
      const newKey = await api.protectedApi('/api-keys', 'POST', { mode: 'live', label: 'plugin-live' });
      const raw = newKey.key || '';
      setKey(raw);
      setShowModal(true);
      try { await navigator.clipboard.writeText(raw); setCopied(true); setTimeout(()=>setCopied(false),1500); setShowToast(true); setTimeout(()=>setShowToast(false),1500);} catch { }
    } catch (err) {
      console.error(err);
      alert('Failed to create key: ' + err);
    } finally {
      setCreating(false);
    }
  };

  const snippet = (k: string) => ` <script src="https://cdn.apiblockchain.io/plugin.min.js"></script>\n<script>\n  ApiBlockchain.init({\n    apiKey: "${k}",\n    mode: "${snippetMode}"\n  });\n</script>`;

  return (
    <AuthGuard>
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
            <button onClick={() => { navigator.clipboard?.writeText(snippet(key)); }} className="bg-green-600 text-white px-3 py-1 rounded">
              Copy snippet
            </button>
          )}
        </div>
      </div>

      <p>Copy the snippet below to integrate the plugin:</p>

      <div className="mt-4">
        <div className="mb-2 flex items-center gap-2">
          <label className="text-sm">Mode</label>
          <select value={showKey ? 'show' : 'hide'} onChange={() => { setShowKey(s => !s); }} className="border rounded p-1">
            <option value="hide">Hide key</option>
            <option value="show">Show key</option>
          </select>
          <div className="ml-4">
            <label className="text-sm">Snippet mode</label>
            <select id="snippet-mode" value={snippetMode} onChange={(e)=>setSnippetMode(e.target.value as any)} className="border rounded p-1 ml-2">
              <option value="live">live</option>
              <option value="test">test</option>
            </select>
          </div>
        </div>

        <pre className="bg-gray-100 p-4 rounded text-sm">
{showKey ? key || 'No key available' : '••••••••••••••••••'}
        </pre>

        {showModal && key && (
          <div className="mt-4 p-4 border rounded bg-yellow-50">
            <p className="font-medium">New key created — copied to clipboard</p>
            <div className="flex items-center gap-4 mt-2">
              <pre className="bg-white p-2 rounded break-all">{key}</pre>
              <div className="flex flex-col gap-2">
                <button onClick={async () => { try { await navigator.clipboard.writeText(key); setCopied(true); setTimeout(()=>setCopied(false),1500);} catch{} }} className="bg-green-600 text-white px-3 py-1 rounded">{copied ? 'Copied!' : 'Copy'}</button>
                <button onClick={() => setShowModal(false)} className="bg-gray-300 text-gray-800 px-3 py-1 rounded">Close</button>
              </div>
            </div>
          </div>
        )}

          <pre className="bg-gray-50 p-4 mt-4 rounded text-sm">
{snippet(key || '')}
        </pre>
      </div>
    </div>
    <Toast open={showToast} message={key ? 'API key created and copied' : 'API key created'} />
    </AuthGuard>
  );
}

export default dynamic(() => Promise.resolve(PluginSetup), { ssr: false });
