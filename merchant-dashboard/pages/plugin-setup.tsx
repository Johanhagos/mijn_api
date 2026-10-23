import { useEffect, useState } from 'react';
import dynamic from 'next/dynamic';
import api from '../lib/api';
import { API_BASE } from '../lib/config';
import AuthGuard from '../components/AuthGuard';
import Toast from '../components/Toast';

// Connect a webshop: create a live API key, then install the WooCommerce plugin (or call
// the API from your own shop's server). The key is shown once and must stay server-side.

function PluginSetup() {
  const [key, setKey] = useState('');
  const [creating, setCreating] = useState(false);
  const [copied, setCopied] = useState(false);
  const [showToast, setShowToast] = useState(false);
  const [wallet, setWallet] = useState<string | null | undefined>(undefined);

  useEffect(() => {
    api.protectedApi('/merchant/me').then((me) => setWallet(me?.payout_wallet || null)).catch(() => setWallet(undefined));
  }, []);

  const copy = async (text: string) => {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      setShowToast(true);
      setTimeout(() => { setCopied(false); setShowToast(false); }, 1500);
    } catch { /* clipboard not available */ }
  };

  const createKey = async () => {
    try {
      setCreating(true);
      const newKey = await api.protectedApi('/api-keys', 'POST', { mode: 'live', label: 'webshop' });
      setKey(newKey.key || '');
      if (newKey.key) copy(newKey.key);
    } catch (err) {
      console.error(err);
      alert('Failed to create key: ' + err);
    } finally {
      setCreating(false);
    }
  };

  const curl = `curl -X POST ${API_BASE}/create_session \\
  -H "X-API-Key: ${key || 'sk_live_...'}" \\
  -H "Content-Type: application/json" \\
  -d '{"amount": 12.50, "order_id": "1042", "customer_email": "jane@example.com",
       "success_url": "https://yourshop.com/thanks", "cancel_url": "https://yourshop.com/cart"}'`;

  return (
    <AuthGuard>
      <div className="p-8 max-w-3xl">
        <h1 className="text-3xl font-bold mb-2">Plugin Setup</h1>
        <p className="text-gray-600 mb-8">Let your webshop customers pay in APIUSD. Orders are marked paid only after the payment is verified on-chain.</p>

        {wallet === null && (
          <div className="bg-yellow-50 border-l-4 border-yellow-400 text-yellow-900 rounded p-4 mb-8">
            Set your payout wallet first: your customers pay straight into it.{' '}
            <a href="/account" className="font-bold underline">Account settings</a>
          </div>
        )}
        {wallet && <p className="text-sm text-gray-600 mb-8">Payments go to your wallet <span className="font-mono">{wallet}</span>.</p>}

        <section className="mb-8">
          <h2 className="text-xl font-bold mb-2">1. Create an API key</h2>
          <p className="text-gray-600 mb-3">The key is shown only once. Keep it secret: paste it in your shop&apos;s settings, never in website code.</p>
          {key ? (
            <div className="p-4 border rounded bg-yellow-50">
              <p className="font-medium mb-2">Your new key {copied ? '(copied)' : ''}</p>
              <div className="flex items-center gap-3">
                <pre className="bg-white p-2 rounded break-all flex-1 text-sm">{key}</pre>
                <button onClick={() => copy(key)} className="bg-green-600 text-white px-3 py-1 rounded">Copy</button>
              </div>
            </div>
          ) : (
            <button onClick={createKey} disabled={creating} className="bg-green-600 text-white px-4 py-2 rounded font-bold disabled:opacity-60">
              {creating ? 'Creating…' : 'Create live API key'}
            </button>
          )}
        </section>

        <section className="mb-8">
          <h2 className="text-xl font-bold mb-2">2. WooCommerce</h2>
          <ol className="list-decimal ml-5 space-y-1 text-gray-700">
            <li><a href="/downloads/apiblockchain-apiusd.zip" className="text-blue-700 underline" download>Download the plugin (apiblockchain-apiusd.zip)</a></li>
            <li>In WordPress: Plugins &gt; Add New &gt; Upload Plugin, choose the zip and activate it.</li>
            <li>WooCommerce &gt; Settings &gt; Payments &gt; <strong>APIBlockchain (APIUSD)</strong>: enable it and paste your API key.</li>
            <li>Your shop currency must be EUR. Customers now see &quot;Pay with APIUSD&quot; at checkout.</li>
          </ol>
        </section>

        <section>
          <h2 className="text-xl font-bold mb-2">Other shops: use the API</h2>
          <p className="text-gray-600 mb-3">
            From your shop&apos;s server, create a checkout session and send the customer to the returned <code>url</code>.
            Check <code>GET /session/&lt;id&gt;/status</code>: when <code>status</code> is <code>paid</code>, complete the order.
          </p>
          <pre className="bg-gray-100 p-4 rounded text-xs overflow-auto">{curl}</pre>
        </section>
      </div>
      <Toast open={showToast} message="Copied" />
    </AuthGuard>
  );
}

export default dynamic(() => Promise.resolve(PluginSetup), { ssr: false });
