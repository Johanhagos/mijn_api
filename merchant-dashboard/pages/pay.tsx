import { useCallback, useEffect, useState } from 'react';
import { useRouter } from 'next/router';
import { QRCodeSVG } from 'qrcode.react';
import { API_BASE, BUY_APIUSD_URL } from '../lib/config';

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
  chain: { id: number; name: string; rpc_urls?: string[]; explorer_url?: string };
  wallet_address: string;
  payment_system?: string;
  currency?: string;
  confirmations_required: number;
  kind?: 'plan' | 'invoice';
  return_url?: string | null;
}

type Tone = 'yellow' | 'red' | 'green' | 'info';
interface Notice { tone: Tone; text: string }

declare global {
  interface Window {
    ethereum?: {
      request: (args: { method: string; params?: any[] }) => Promise<any>;
      on?: (event: string, handler: (...args: any[]) => void) => void;
      removeListener?: (event: string, handler: (...args: any[]) => void) => void;
    };
  }
}

// "12.500000" -> "12.50" (cut, not rounded, so a short balance never shows as enough)
const fmt2 = (amount: string) => {
  const [whole, frac = ''] = String(amount).split('.');
  return `${whole}.${(frac + '00').slice(0, 2)}`;
};

const unitsToFixed2 = (units: bigint, decimals: number) => {
  const s = units.toString().padStart(decimals + 1, '0');
  return fmt2(`${s.slice(0, s.length - decimals)}.${s.slice(s.length - decimals)}`);
};

const pad32 = (hex: string) => hex.replace(/^0x/, '').padStart(64, '0');

// ERC-20 transfer(address,uint256)
const encodeTransfer = (to: string, units: string) =>
  '0xa9059cbb' + pad32(to.toLowerCase()) + pad32(BigInt(units).toString(16));

// ERC-20 balanceOf(address)
const encodeBalanceOf = (owner: string) => '0x70a08231' + pad32(owner.toLowerCase());

const PAID_STATUSES = ['paid', 'overpaid'];

export default function PayInvoice() {
  const router = useRouter();
  const { invoice: id } = router.query;
  const [view, setView] = useState<PaymentView | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [manualTx, setManualTx] = useState('');
  const [notice, setNotice] = useState<Notice | null>(null);
  const [account, setAccount] = useState<string | null>(null);
  const [chainId, setChainId] = useState<number | null>(null);
  const [balance, setBalance] = useState<bigint | null>(null);

  const symbol = view?.token.symbol || 'APIUSD';
  const failedText = `Payment failed. No ${symbol} left your wallet. Please try again.`;

  const noticeFor = useCallback((result?: PaymentView['results'][number], body?: PaymentView): Notice | null => {
    if (!result) return null;
    if (result.state === 'confirmed') return { tone: 'green', text: 'Payment received.' };
    if (result.state === 'failed') return { tone: 'red', text: failedText };
    if (result.state === 'rejected') return { tone: 'red', text: result.reason || 'The transaction was not accepted' };
    if (result.state === 'pending' && body) {
      return { tone: 'info', text: `Transaction sent. Waiting for ${body.confirmations_required} confirmations on ${body.chain.name}…` };
    }
    return null;
  }, [failedText]);

  const load = useCallback(async () => {
    if (!id) return;
    try {
      const res = await fetch(`${API_BASE}/pay/${id}`);
      if (!res.ok) throw new Error(res.status === 404 ? 'Invoice not found' : 'Could not load the invoice');
      const body: PaymentView = await res.json();
      setView(body);
      setError(null);
      // Pending transactions re-checked by the backend on this load
      const settled = body.results.find((r) => r.state !== 'pending');
      if (settled) setNotice(noticeFor(settled, body));
    } catch (err: any) {
      setError(err.message);
    }
  }, [id, noticeFor]);

  useEffect(() => {
    load();
  }, [load]);

  // While a transaction waits for confirmations, poll; the backend re-checks it on each load.
  useEffect(() => {
    if (!view || view.pending_txs.length === 0 || PAID_STATUSES.includes(view.status)) return;
    const t = setInterval(load, 10000);
    return () => clearInterval(t);
  }, [view, load]);

  const wantedChain = view?.chain.id;
  const tokenAddress = view?.token.address;

  // Reads the connected account, its network and its APIUSD balance without opening the wallet.
  const refreshWallet = useCallback(async () => {
    const eth = window.ethereum;
    if (!eth || !wantedChain || !tokenAddress) return;
    try {
      const [acc] = await eth.request({ method: 'eth_accounts' });
      const cid = parseInt(await eth.request({ method: 'eth_chainId' }), 16);
      setAccount(acc || null);
      setChainId(cid);
      if (acc && cid === wantedChain) {
        const raw = await eth.request({ method: 'eth_call', params: [{ to: tokenAddress, data: encodeBalanceOf(acc) }, 'latest'] });
        setBalance(BigInt(raw && raw !== '0x' ? raw : 0));
      } else {
        setBalance(null);
      }
    } catch {
      setBalance(null);
    }
  }, [wantedChain, tokenAddress]);

  // Re-read on wallet changes and when the payer comes back to this tab (e.g. from the buy page).
  useEffect(() => {
    refreshWallet();
    const eth = window.ethereum;
    const onVisible = () => { if (document.visibilityState === 'visible') refreshWallet(); };
    eth?.on?.('accountsChanged', refreshWallet);
    eth?.on?.('chainChanged', refreshWallet);
    window.addEventListener('focus', refreshWallet);
    document.addEventListener('visibilitychange', onVisible);
    return () => {
      eth?.removeListener?.('accountsChanged', refreshWallet);
      eth?.removeListener?.('chainChanged', refreshWallet);
      window.removeEventListener('focus', refreshWallet);
      document.removeEventListener('visibilitychange', onVisible);
    };
  }, [refreshWallet]);

  // The wallet can answer from a slightly old block, so keep re-reading while the balance is short.
  const neededUnits = view?.amount_remaining_units;
  useEffect(() => {
    if (!account || balance === null || !neededUnits || balance >= BigInt(neededUnits)) return;
    const t = setInterval(() => {
      if (document.visibilityState === 'visible') refreshWallet();
    }, 4000);
    return () => clearInterval(t);
  }, [account, balance, neededUnits, refreshWallet]);

  const submitTx = async (txHash: string) => {
    const res = await fetch(`${API_BASE}/pay/${id}/transactions`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ tx_hash: txHash }),
    });
    const body = await res.json();
    if (body && body.invoice_id) setView(body);
    const result = body?.results?.[0];
    if (!res.ok && !result) {
      setNotice({ tone: 'red', text: body?.detail || 'The transaction was not accepted' });
      return;
    }
    setNotice(noticeFor(result, body));
  };

  const connectWallet = async () => {
    if (!window.ethereum) {
      setNotice({ tone: 'info', text: 'No wallet found. Install MetaMask, or pay from another wallet and paste the transaction hash below.' });
      return;
    }
    try {
      await window.ethereum.request({ method: 'eth_requestAccounts' });
    } catch {
      return; // closed or rejected in the wallet: nothing changes
    }
    await refreshWallet();
  };

  const switchNetwork = async () => {
    if (!window.ethereum || !view) return;
    const chainHex = '0x' + view.chain.id.toString(16);
    try {
      await window.ethereum.request({ method: 'wallet_switchEthereumChain', params: [{ chainId: chainHex }] });
    } catch (switchErr: any) {
      if (switchErr?.code !== 4902) return;
      try {
        await window.ethereum.request({
          method: 'wallet_addEthereumChain',
          params: [{
            chainId: chainHex,
            chainName: view.chain.name,
            nativeCurrency: { name: 'Ether', symbol: 'ETH', decimals: 18 },
            rpcUrls: view.chain.rpc_urls && view.chain.rpc_urls.length ? view.chain.rpc_urls : [],
            blockExplorerUrls: view.chain.explorer_url ? [view.chain.explorer_url] : [],
          }],
        });
      } catch {
        return;
      }
    }
    await refreshWallet();
  };

  const payWithWallet = async () => {
    if (!view || !window.ethereum || !account) return;
    setBusy(true);
    setNotice(null);
    try {
      const cid = parseInt(await window.ethereum.request({ method: 'eth_chainId' }), 16);
      if (cid !== view.chain.id) {
        setChainId(cid); // shows the switch-network notice; nothing is sent
        return;
      }
      const txHash = await window.ethereum.request({
        method: 'eth_sendTransaction',
        params: [{ from: account, to: view.token.address, data: encodeTransfer(view.wallet_address, view.amount_remaining_units) }],
      });
      await submitTx(txHash);
    } catch (err: any) {
      if (err?.code === 4001) return; // rejected in the wallet: back to the page, nothing changed
      setNotice({ tone: 'red', text: failedText });
    } finally {
      setBusy(false);
      refreshWallet();
    }
  };

  const submitManual = async () => {
    if (!manualTx.trim()) return;
    setBusy(true);
    setNotice(null);
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

  const paid = PAID_STATUSES.includes(view.status);
  const needed = BigInt(view.amount_remaining_units || '0');
  const wrongNetwork = !!account && chainId !== null && chainId !== view.chain.id;
  const shortOfFunds = !!account && !wrongNetwork && balance !== null && balance < needed;
  const confirming = view.pending_txs.length > 0;
  const canPay = !!account && !wrongNetwork && balance !== null && !shortOfFunds && !busy && !confirming;
  const amountText = fmt2(view.amount_remaining);
  const unit = view.payment_system === 'web2' ? (view.currency || 'EUR') : symbol;
  const paymentUri = `ethereum:${view.token.address}@${view.chain.id}/transfer?address=${view.wallet_address}&uint256=${view.amount_remaining_units}`;

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
          {view.status === 'overpaid' ? 'Overpaid' : paid ? 'Paid' : view.status === 'partially_paid' ? 'Partly paid' : 'Open'}
        </span>
      </div>

      <div className="grid grid-cols-3 gap-4 mb-6 text-center">
        <Amount label="Total" value={view.amount_due} symbol={unit} />
        <Amount label="Paid" value={view.amount_paid} symbol={unit} />
        <Amount label="Still to pay" value={view.amount_remaining} symbol={unit} strong />
      </div>

      {!paid && view.payable && (
        <>
          <p className="text-sm font-bold text-gray-700 mb-2">Pay with</p>
          <label className="flex items-center justify-between border-2 border-blue-600 rounded-lg px-4 py-3 mb-2 cursor-pointer">
            <span className="flex items-center gap-3">
              <input type="radio" name="asset" checked readOnly className="accent-blue-600" />
              <span className="font-bold text-gray-900">{symbol} — {amountText}</span>
            </span>
            <span className="text-xs text-gray-500">{view.chain.name}</span>
          </label>
          <a href={BUY_APIUSD_URL} target="_blank" rel="noopener noreferrer"
             className="inline-block text-sm text-blue-700 hover:underline mb-4">
            Don&apos;t have {symbol}? Buy it here
          </a>

          {wrongNetwork && (
            <NoticeBox tone="yellow">
              <p>Switch your wallet to {view.chain.name} to pay with {symbol}.</p>
              <button onClick={switchNetwork} className="mt-2 px-3 py-1 rounded bg-yellow-600 text-white text-sm font-bold">
                Switch to {view.chain.name}
              </button>
            </NoticeBox>
          )}

          {shortOfFunds && (
            <NoticeBox tone="yellow">
              <p>Not enough {symbol}. You have {unitsToFixed2(balance as bigint, view.token.decimals)} {symbol}, this invoice needs {amountText} {symbol}.</p>
              <a href={BUY_APIUSD_URL} target="_blank" rel="noopener noreferrer"
                 className="inline-block mt-2 px-3 py-1 rounded bg-yellow-600 text-white text-sm font-bold">
                Buy {symbol}
              </a>
            </NoticeBox>
          )}

          {account ? (
            <button
              onClick={payWithWallet}
              disabled={!canPay}
              className="w-full py-3 rounded-lg bg-blue-600 text-white font-bold hover:bg-blue-700 disabled:opacity-60 mb-4 flex items-center justify-center gap-2"
            >
              {busy ? (
                <><Spinner /> Waiting for your wallet…</>
              ) : confirming ? (
                <><Spinner /> Confirming payment…</>
              ) : (
                `Pay ${amountText} ${symbol}`
              )}
            </button>
          ) : (
            <button
              onClick={connectWallet}
              className="w-full py-3 rounded-lg bg-blue-600 text-white font-bold hover:bg-blue-700 mb-4"
            >
              Connect wallet
            </button>
          )}

          <div className="text-sm text-gray-600 bg-gray-50 rounded-lg p-4 mb-4 space-y-1">
            <p><strong>Paying from another wallet?</strong> Scan the code, or send exactly {amountText} {symbol} on {view.chain.name} to:</p>
            <div className="flex justify-center py-2">
              <QRCodeSVG value={paymentUri} size={160} />
            </div>
            <p className="font-mono break-all text-gray-900">{view.wallet_address}</p>
            <p>Token contract: <span className="font-mono break-all">{view.token.address}</span></p>
            <p>Then paste the transaction hash here:</p>
            <div className="flex gap-2 pt-1">
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
        view.payment_system === 'web2' ? (
          <NoticeBox tone="info">
            <p>This invoice is paid by bank transfer or card, not in {symbol}. Please contact {view.seller_name || 'the seller'} for the payment details.</p>
          </NoticeBox>
        ) : (
          <p className="text-gray-600 mb-4">This invoice cannot be paid online.</p>
        )
      )}

      {notice && <NoticeBox tone={notice.tone}><p>{notice.text}</p></NoticeBox>}

      {paid && view.return_url && (
        <a href={view.return_url}
           className="block w-full py-3 mb-4 rounded-lg bg-green-600 text-white font-bold text-center hover:bg-green-700">
          {view.kind === 'plan' ? 'Your plan is active — go to the dashboard' : 'Back to the shop'}
        </a>
      )}

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
              <span>{fmt2(p.amount)} {symbol}</span>
            </a>
          ))}
        </div>
      )}
    </Shell>
  );
}

const TONES: Record<Tone, string> = {
  yellow: 'bg-yellow-50 border-yellow-400 text-yellow-900',
  red: 'bg-red-50 border-red-400 text-red-900',
  green: 'bg-green-50 border-green-500 text-green-900',
  info: 'bg-blue-50 border-blue-300 text-gray-800',
};

function NoticeBox({ tone, children }: { tone: Tone; children: React.ReactNode }) {
  return <div role="status" className={`text-sm border-l-4 rounded p-3 mb-4 ${TONES[tone]}`}>{children}</div>;
}

function Spinner() {
  return (
    <svg className="animate-spin h-5 w-5" viewBox="0 0 24 24" fill="none" aria-hidden="true">
      <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" className="opacity-25" />
      <path d="M22 12a10 10 0 0 1-10 10" stroke="currentColor" strokeWidth="4" strokeLinecap="round" />
    </svg>
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
        {fmt2(value)}
      </p>
      <p className="text-xs text-gray-500">{symbol}</p>
    </div>
  );
}
