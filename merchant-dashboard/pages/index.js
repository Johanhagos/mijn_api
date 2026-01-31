import { useEffect, useState } from 'react';
import { api } from '../lib/api';

export default function Home() {
  const [status, setStatus] = useState('loading');

  useEffect(() => {
    (async () => {
      try {
        const res = await api('/health');
        setStatus(res.status || JSON.stringify(res));
      } catch (e) {
        setStatus('error: ' + e.message);
      }
    })();
  }, []);

  return (
    <main style={{ padding: 20, fontFamily: 'sans-serif' }}>
      <h1>Merchant Dashboard</h1>
      <p>
        Backend status: <strong>{status}</strong>
      </p>
      <p>
        <button
          onClick={async () => {
            try {
              const invoices = await api('/invoices');
              console.log('invoices', invoices);
              alert('Fetched invoices — check the browser console');
            } catch (e) {
              alert('Error: ' + e.message);
            }
          }}
        >
          Fetch invoices
        </button>
      </p>
    </main>
  );
}
