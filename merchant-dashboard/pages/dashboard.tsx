import { useEffect, useState } from 'react';
import Link from 'next/link';
import api from '../lib/api';
import AuthGuard from '../components/AuthGuard';
import RevenueChart from '../components/RevenueChart';
import PaymentDonut from '../components/PaymentDonut';
import ApiKeysList from '../components/ApiKeysList';
import PluginSetup from '../components/PluginSetup';
import VATChecker from '../components/VATChecker';

export default function Dashboard() {
  const [stats, setStats] = useState<any>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [apiKeys, setApiKeys] = useState<any[]>([]);
  const [merchant, setMerchant] = useState<any>(null);

  useEffect(() => {
    let mounted = true;

    const fetchData = async () => {
      setLoading(true);
      try {
        const [usage, keys, me] = await Promise.all([
          api.protectedApi('/merchant/usage'),
          api.protectedApi('/api-keys'),
          api.protectedApi('/merchant/me'),
        ]);
        if (!mounted) return;
        setStats(usage);
        setApiKeys(keys || []);
        setMerchant(me);
      } catch (e) {
        console.error(e);
      } finally {
        if (mounted) setLoading(false);
      }
    };

    fetchData();
    const interval = setInterval(fetchData, 3000);
    return () => {
      mounted = false;
      clearInterval(interval);
    };
  }, []);

  const handleRevoke = (id: any) => {
    api.protectedApi(`/api-keys/${id}`, 'DELETE')
      .then(() => setApiKeys((ks) => ks.filter((k: any) => k.id !== id)))
      .catch(() => alert('Failed to revoke'));
  };

  const revenueData = (stats?.revenue || []).map((r: any) => ({ 
    date: new Date(r.date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' }), 
    amount: r.amount 
  }));
  const donutData = [
    { name: 'Web2', value: stats?.web2_total || 0 },
    { name: 'Web3', value: stats?.web3_total || 0 },
  ];

  return (
    <AuthGuard>
      <div className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100">
        {/* Header */}
        <header className="bg-white shadow-sm border-b border-gray-200">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
            <div className="flex items-center justify-between">
              <div>
                <h1 className="text-3xl font-bold text-gray-900">Dashboard</h1>
                <p className="text-sm text-gray-600 mt-1">Welcome back, {merchant?.name || 'Merchant'}</p>
              </div>
              <div className="flex gap-3">
                <Link href="/invoices/create" className="inline-flex items-center px-4 py-2 rounded-lg bg-green-600 text-white hover:bg-green-700 font-medium transition shadow-sm">
                  ➕ New Invoice
                </Link>
                <Link href="/invoices" className="inline-flex items-center px-4 py-2 rounded-lg bg-slate-200 text-slate-900 hover:bg-slate-300 font-medium transition">
                  📄 Invoices
                </Link>
                <Link href="/api-keys" className="inline-flex items-center px-4 py-2 rounded-lg bg-slate-200 text-slate-900 hover:bg-slate-300 font-medium transition">
                  🔑 API Keys
                </Link>
              </div>
            </div>
          </div>
        </header>

        <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          {/* Key Metrics */}
          <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
            <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6 hover:shadow-md transition">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-gray-600">Total Revenue</p>
                  <p className="text-3xl font-bold text-gray-900 mt-2">{stats?.total_amount ? `€${parseFloat(stats.total_amount).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}` : '—'}</p>
                </div>
                <div className="text-4xl opacity-10">💰</div>
              </div>
              <div className="mt-4 text-xs text-gray-500">All time earnings</div>
            </div>

            <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6 hover:shadow-md transition">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-gray-600">Web2 Transactions</p>
                  <p className="text-3xl font-bold text-green-600 mt-2">{stats?.web2_count ?? '—'}</p>
                </div>
                <div className="text-4xl opacity-10">💳</div>
              </div>
              <div className="mt-4 text-xs text-gray-500">Card & payment methods</div>
            </div>

            <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6 hover:shadow-md transition">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-gray-600">Web3 Transactions</p>
                  <p className="text-3xl font-bold text-purple-600 mt-2">{stats?.web3_count ?? '—'}</p>
                </div>
                <div className="text-4xl opacity-10">🔗</div>
              </div>
              <div className="mt-4 text-xs text-gray-500">Blockchain payments</div>
            </div>

            <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6 hover:shadow-md transition">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-gray-600">Active API Keys</p>
                  <p className="text-3xl font-bold text-blue-600 mt-2">{apiKeys.length}</p>
                </div>
                <div className="text-4xl opacity-10">🔐</div>
              </div>
              <div className="mt-4 text-xs text-gray-500">{apiKeys.filter((k: any) => k.mode === 'live').length} live keys</div>
            </div>
          </div>

          {/* Charts Section */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-8">
            <div className="lg:col-span-2 bg-white rounded-lg shadow-sm border border-gray-200 p-6">
              <div className="mb-6">
                <h2 className="text-lg font-semibold text-gray-900">Revenue Trend</h2>
                <p className="text-sm text-gray-600">Transaction volume over time</p>
              </div>
              <RevenueChart data={revenueData.length ? revenueData : [{ date: '01', amount: 0 }]} />
            </div>

            <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
              <div className="mb-6">
                <h2 className="text-lg font-semibold text-gray-900">Payment Mix</h2>
                <p className="text-sm text-gray-600">Web2 vs Web3 distribution</p>
              </div>
              <PaymentDonut data={donutData} />
            </div>
          </div>

          {/* VAT Section */}
          <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6 mb-8">
            <div className="mb-6">
              <h2 className="text-lg font-semibold text-gray-900">VAT Compliance</h2>
              <p className="text-sm text-gray-600">Validate and check VAT numbers</p>
            </div>
            <VATChecker />
          </div>

          {/* Bottom Section */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            <div className="lg:col-span-2 bg-white rounded-lg shadow-sm border border-gray-200 p-6">
              <div className="mb-6">
                <h2 className="text-lg font-semibold text-gray-900">API Keys</h2>
                <p className="text-sm text-gray-600">Manage your API credentials</p>
              </div>
              <ApiKeysList keys={apiKeys.map((k: any) => ({ id: k.id, key_type: k.type, masked: k.masked || k.id, created_at: k.created_at }))} onRevoke={handleRevoke} />
            </div>

            <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
              <div className="mb-6">
                <h2 className="text-lg font-semibold text-gray-900">Plugin Setup</h2>
                <p className="text-sm text-gray-600">Integrate with your site</p>
              </div>
              <PluginSetup snippet={`<script src="/plugin.js"></script>`} />
            </div>
          </div>

          {/* Footer Info */}
          <div className="mt-8 p-4 bg-blue-50 border border-blue-200 rounded-lg">
            <p className="text-sm text-blue-900">
              <span className="font-semibold">💡 Tip:</span> Use the API to automate invoice creation and payment tracking. Check out our documentation for integration examples.
            </p>
          </div>
        </main>
      </div>
    </AuthGuard>
  );
}
