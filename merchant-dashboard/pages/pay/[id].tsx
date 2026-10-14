import { useCallback, useEffect, useState } from 'react';
import { useRouter } from 'next/router';
import { API_BASE } from '../../lib/config';

// Public page where a customer pays an invoice in APIUSD. The backend only marks the
// invoice paid after it has verified the transaction on-chain; this page just helps send
// the transaction and shows the status.

interface PaymentView {
  invoice_id: string;
  invoice_number?: string;
  seller_name?: string;
  buyer_name?: string;
  status: string;
  amount_due: string;
  amount_paid: string;
  amount_remaining: string;
  amount_remaining_units: string;
  payable: boolean;
  pending_txs: string[];
  payments: { tx_hash: string; amount: string; explorer_url: string }[];
  results: { tx_hash: string; state: string; reason?: string; confirmations?: number; required?: number }[];
  token: { symbol: string; address: string; decimals: number };
  chain: { id: number; name: string };
  wallet_address: string;
  confirmations_required: number;
}

declare global {
  interface Window {
    ethereum?: { request: (args: { method: string; params?: any[] }) => Promise<any> };
  }
}

// 12.500000 -> 12.5
const fmt = (amount: string) => String(Number(amount));

const pad32 = (hex: string) => hex.replace(/^0x/, '').padStart(64, '0');

// ERC-20 transfer(address,uint256)
const encodeTransfer = (to: string, units: string) =>
  '0xa9059cbb' + pad32(to.toLowerCase()) + pad32(BigInt(units).toString(16));

export default function PayInvoice() {
  const router = useRouter();
  const { id } = router.query;
  const [view, setView] = useState<PaymentView | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [manualTx, setManualTx] = useState('');
  const [message, setMessage] = useState<string | null>(null);

  const load = useCallback(async () => {
    if (!id) return;
    try {
      const res = await fetch(`${API_BASE}/pay/${id}`);
      if (!res.ok) throw new Error(res.status === 404 ? 'Invoice not found' : 'Could not load the invoice');
      setView(await res.json());
      setError(null);
    } catch (err: any) {
      setError(err.message);
    }
  }, [id]);

  useEffect(() => {
    load();
  }, [load]);

  // While a transaction waits for confirmations, poll; the backend re-checks it on each load.
  useEffect(() => {
    if (!view || view.pending_txs.length === 0 || view.status === 'paid') return;
    const t = setInterval(load, 10000);
    return () => clearInterval(t);
  }, [view, load]);

  const submitTx = async (txHash: string) => {
    const res = await fetch(`${API_BASE}/pay/${id}/transactions`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ tx_hash: txHash }),
    });
    const body = await res.json();
    if (body && body.invoice_id) setView(body);
    const result = body?.results?.[0];
    if (!res.ok) {
      setMessage(result?.reason || body?.detail || 'The transaction was not accepted');
    } else if (result?.state === 'pending') {
      setMessage(`Transaction sent. Waiting for ${body.confirmations_required} confirmations on ${body.chain.name}…`);
    } else if (result?.state === 'confirmed') {
      setMessage('Payment confirmed.');
    }
  };

  const payWithWallet = async () => {
    if (!view) return;
    if (!window.ethereum) {
      setMessage('No wallet found. Install MetaMask, or pay from another wallet and paste the transaction hash below.');
      return;
    }
    setBusy(true);
    setMessage(null);
    try {
      const [from] = await window.ethereum.request({ method: 'eth_requestAccounts' });
      const chainHex = '0x' + view.chain.id.toString(16);
      try {
        await window.ethereum.request({ method: 'wallet_switchEthereumChain', params: [{ chainId: chainHex }] });
      } catch (switchErr: any) {
        if (switchErr?.code === 4902) {
          await window.ethereum.request({
            method: 'wallet_addEthereumChain',
            params: [{
              chainId: chainHex,
              chainName: view.chain.name,
              nativeCurrency: { name: 'Sepolia ETH', symbol: 'ETH', decimals: 18 },
              rpcUrls: ['https://ethereum-sepolia-rpc.publicnode.com'],
              blockExplorerUrls: ['https://sepolia.etherscan.io'],
            }],
          });
        } else {
          throw switchErr;
        }
      }
      const txHash = await window.ethereum.request({
        method: 'eth_sendTransaction',
        params: [{ from, to: view.token.address, data: encodeTransfer(view.wallet_address, view.amount_remaining_units) }],
      });
      await submitTx(txHash);
    } catch (err: any) {
      setMessage(err?.code === 4001 ? 'Payment cancelled in your wallet.' : err?.message || 'Payment failed');
    } finally {
      setBusy(false);
    }
  };

  const submitManual = async () => {
    if (!manualTx.trim()) return;
    setBusy(true);
    setMessage(null);
    try {
      await submitTx(manualTx.trim());
      setManualTx('');
    } finally {
      setBusy(false);
    }
  };

  if (error) {
    return <Shell><p className="text-red-600">{error}</p></Shell>;
  }
  if (!view) {
    return <Shell><p className="text-gray-600">Loading…</p></Shell>;
  }

  const paid = view.status === 'paid';
  return (
    <Shell>
      <div className="flex justify-between items-start mb-6">
        <div>
          <p className="text-sm text-gray-500">Invoice</p>
          <h1 className="text-2xl font-bold text-gray-900">{view.invoice_number || view.invoice_id}</h1>
          {view.seller_name && <p className="text-gray-600">from {view.seller_name}</p>}
        </div>
        <span className={`px-3 py-1 rounded-full text-sm font-bold ${
          paid ? 'bg-green-100 text-green-800'
            : view.status === 'partially_paid' ? 'bg-yellow-100 text-yellow-800'
            : 'bg-gray-100 text-gray-800'}`}>
          {paid ? 'Paid' : view.status === 'partially_paid' ? 'Partly paid' : 'Open'}
        </span>
      </div>

      <div className="grid grid-cols-3 gap-4 mb-6 text-center">
        <Amount label="Total" value={view.amount_due} symbol={view.token.symbol} />
        <Amount label="Paid" value={view.amount_paid} symbol={view.token.symbol} />
        <Amount label="Still to pay" value={view.amount_remaining} symbol={view.token.symbol} strong />
      </div>

      {!paid && view.payable && (
        <>
          <button
            onClick={payWithWallet}
            disabled={busy}
            className="w-full py-3 rounded-lg bg-blue-600 text-white font-bold hover:bg-blue-700 disabled:opacity-60 mb-4"
          >
            {busy ? 'Waiting for your wallet…' : `Pay ${fmt(view.amount_remaining)} ${view.token.symbol} with MetaMask`}
          </button>

          <div className="text-sm text-gray-600 bg-gray-50 rounded-lg p-4 mb-4 space-y-1">
            <p><strong>Paying from another wallet?</strong> Send exactly {fmt(view.amount_remaining)} {view.token.symbol} on {view.chain.name} to:</p>
            <p className="font-mono break-all text-gray-900">{view.wallet_address}</p>
            <p>Token contract: <span className="font-mono break-all">{view.token.address}</span></p>
            <div className="flex gap-2 pt-2">
              <input
                value={manualTx}
                onChange={(e) => setManualTx(e.target.value)}
                placeholder="Transaction hash (0x…)"
                className="flex-1 px-3 py-2 border border-gray-300 rounded-lg font-mono text-xs"
              />
              <button onClick={submitManual} disabled={busy} className="px-4 py-2 rounded-lg bg-gray-800 text-white text-sm font-bold disabled:opacity-60">
                Check
              </button>
            </div>
          </div>
        </>
      )}

      {!paid && !view.payable && (
        <p className="text-gray-600 mb-4">This invoice cannot be paid online.</p>
      )}

      {message && <p className="text-sm text-gray-800 bg-blue-50 rounded p-3 mb-4">{message}</p>}

      {view.pending_txs.length > 0 && !paid && (
        <p className="text-sm text-yellow-800 mb-4">
          Waiting for {view.confirmations_required} blockchain confirmations. This page updates by itself.
        </p>
      )}

      {view.payments.length > 0 && (
        <div className="border-t pt-4">
          <p className="text-sm font-bold text-gray-700 mb-2">Confirmed payments</p>
          {view.payments.map((p) => (
            <a key={p.tx_hash} href={p.explorer_url} target="_blank" rel="noopener noreferrer"
               className="flex justify-between text-sm text-blue-700 hover:underline">
              <span className="font-mono">{p.tx_hash.slice(0, 18)}…</span>
              <span>{fmt(p.amount)} {view.token.symbol}</span>
            </a>
          ))}
        </div>
      )}
    </Shell>
  );
}

function Shell({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center px-4 py-10">
      <div className="max-w-lg w-full bg-white rounded-lg shadow p-8">{children}</div>
    </div>
  );
}

function Amount({ label, value, symbol, strong }: { label: string; value: string; symbol: string; strong?: boolean }) {
  return (
    <div>
      <p className="text-xs text-gray-500 uppercase">{label}</p>
      <p className={`${strong ? 'text-xl font-bold' : 'text-lg font-semibold'} text-gray-900`}>
        {Number(value).toFixed(2)}
      </p>
      <p className="text-xs text-gray-500">{symbol}</p>
    </div>
  );
}
