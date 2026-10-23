import { useEffect, useState } from 'react';
import { useRouter } from 'next/router';
import api from '../lib/api';
import { API_BASE } from '../lib/config';

// Choose and pay for a plan. Paying opens the APIUSD payment page; the backend activates
// the plan only after the payment is verified on-chain, and the dashboard needs an active plan.

interface Plan {
  id: string;
  name: string;
  price: number | null;
  currency: string;
  period_days: number;
  monthly_invoices: number | null;
  description: string;
  purchasable: boolean;
}

interface Quote {
  country: string | null;
  vat_note: string | null;
  plans: { id: string; subtotal?: number; vat_rate?: number; vat_amount?: number; total?: number }[];
}

interface Me {
  name?: string;
  plan?: string | null;
  plan_name?: string | null;
  plan_active?: boolean;
  plan_expires_at?: string | null;
}

export default function Plans() {
  const router = useRouter();
  const wanted = typeof router.query.plan === 'string' ? router.query.plan : null;
  const [plans, setPlans] = useState<Plan[]>([]);
  const [me, setMe] = useState<Me | null>(null);
  const [quote, setQuote] = useState<Quote | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!router.isReady) return;
    if (!localStorage.getItem('jwt')) {
      // New visitors create an account first, then come back here
      router.replace(`/signup${wanted ? `?plan=${encodeURIComponent(wanted)}` : ''}`);
      return;
    }
    (async () => {
      try {
        const [list, info, prices] = await Promise.all([
          fetch(`${API_BASE}/plans`).then((r) => r.json()),
          api.protectedApi('/merchant/me'),
          api.protectedApi('/plans/quote'),
        ]);
        setPlans(list);
        setMe(info);
        setQuote(prices);
      } catch (err: any) {
        setError('Could not load the plans. Please try again.');
      }
    })();
  }, [router, router.isReady, wanted]);

  const buy = async (planId: string) => {
    setBusy(planId);
    setError(null);
    try {
      const res = await api.protectedApi('/plans/checkout', 'POST', { plan: planId });
      window.location.href = `/pay?invoice=${encodeURIComponent(res.invoice_id)}`;
    } catch (err: any) {
      let detail = 'Could not start the payment. Please try again.';
      try { detail = JSON.parse(err.message).detail || detail; } catch { /* plain text */ }
      setError(detail);
      setBusy(null);
    }
  };

  const priceFor = (id: string) => quote?.plans.find((q) => q.id === id);
  const needsCountry = quote !== null && !quote.country;
  const until = me?.plan_expires_at ? new Date(me.plan_expires_at).toLocaleDateString() : null;

  return (
    <div className="min-h-screen bg-gray-50 px-4 py-12">
      <div className="max-w-4xl mx-auto">
        <h1 className="text-3xl font-bold text-gray-900 text-center mb-2">Choose your plan</h1>
        <p className="text-gray-600 text-center mb-8">
          Pay in APIUSD. Your dashboard, API keys and webshop checkout are unlocked as soon as the payment is confirmed.
        </p>

        {me?.plan_active && (
          <div className="bg-green-50 border-l-4 border-green-500 text-green-900 rounded p-4 mb-6 flex justify-between items-center">
            <span>Your {me.plan_name} plan is active{until ? ` until ${until}` : ''}. Paying again adds another period.</span>
            <a href="/dashboard" className="px-4 py-2 rounded bg-green-600 text-white font-bold text-sm">Go to dashboard</a>
          </div>
        )}
        {me && !me.plan_active && me.plan && (
          <div className="bg-yellow-50 border-l-4 border-yellow-400 text-yellow-900 rounded p-4 mb-6">
            Your {me.plan_name} plan has ended{until ? ` on ${until}` : ''}. Renew it to use the dashboard and your webshop checkout again.
          </div>
        )}
        {needsCountry && (
          <div className="bg-yellow-50 border-l-4 border-yellow-400 text-yellow-900 rounded p-4 mb-6">
            Set your country first: the VAT on your plan depends on it.{' '}
            <a href="/account" className="font-bold underline">Go to Account settings</a>
          </div>
        )}
        {quote?.vat_note && <p className="text-center text-sm text-gray-600 mb-6">VAT: {quote.vat_note}</p>}
        {error && <div className="bg-red-50 border-l-4 border-red-400 text-red-900 rounded p-4 mb-6">{error}</div>}

        <div className="grid md:grid-cols-3 gap-6">
          {plans.map((p) => (
            <div key={p.id}
                 className={`bg-white rounded-lg shadow p-6 flex flex-col ${wanted === p.id ? 'ring-2 ring-blue-600' : ''}`}>
              <h2 className="text-xl font-bold text-gray-900">{p.name}</h2>
              <p className="text-3xl font-bold text-gray-900 mt-3">
                {p.price === null ? 'Custom' : `€${p.price.toFixed(2)}`}
                {p.price !== null && <span className="text-base font-normal text-gray-500"> / {p.period_days} days</span>}
              </p>
              {p.price !== null && <p className="text-xs text-gray-500 mb-3">excl. VAT</p>}
              <p className="text-gray-600 flex-1">{p.description}</p>
              {p.purchasable && priceFor(p.id)?.total !== undefined && (
                <div className="text-sm text-gray-700 mt-4 border-t pt-3 space-y-1">
                  <div className="flex justify-between"><span>Price</span><span>€{priceFor(p.id)!.subtotal!.toFixed(2)}</span></div>
                  <div className="flex justify-between"><span>VAT {priceFor(p.id)!.vat_rate}%</span><span>€{priceFor(p.id)!.vat_amount!.toFixed(2)}</span></div>
                  <div className="flex justify-between font-bold"><span>Total</span><span>€{priceFor(p.id)!.total!.toFixed(2)}</span></div>
                </div>
              )}
              {p.purchasable ? (
                <button onClick={() => buy(p.id)} disabled={busy !== null || needsCountry}
                        className="mt-6 w-full py-3 rounded-lg bg-blue-600 text-white font-bold hover:bg-blue-700 disabled:opacity-60">
                  {busy === p.id ? 'Opening payment…'
                    : `Pay ${(priceFor(p.id)?.total ?? p.price ?? 0).toFixed(2)} APIUSD`}
                </button>
              ) : (
                <a href="mailto:sales@apiblockchain.io?subject=Enterprise%20plan"
                   className="mt-6 w-full py-3 rounded-lg bg-gray-800 text-white font-bold text-center hover:bg-gray-900">
                  Contact us
                </a>
              )}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
