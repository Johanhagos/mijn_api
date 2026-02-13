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
      <div className="min-h-screen bg-slate-900 relative">
        {/* Background Image with Overlay */}
        <div 
          className="fixed inset-0 z-0 opacity-20"
          style={{
            backgroundImage: 'url(https://images.unsplash.com/photo-1639762681485-074b7f938ba0?w=1920&q=90)',
            backgroundSize: 'cover',
            backgroundPosition: 'center',
            backgroundAttachment: 'fixed'
          }}
        />
        <div className="fixed inset-0 z-0 bg-gradient-to-br from-emerald-900/80 via-slate-900/90 to-slate-950/95" />
        
        {/* Content */}
        <div className="relative z-10">
          {/* Header */}
          <header className="bg-slate-800/80 backdrop-blur-sm shadow-lg border-b border-emerald-700/30">
            <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
              <div className="flex items-center justify-between">
                <div>
                  <h1 className="text-3xl font-bold text-white">Dashboard</h1>
                  <p className="text-sm text-emerald-300 mt-1">Welcome back, {merchant?.name || 'Merchant'}</p>
                </div>
                <div className="flex gap-3">
                  <Link href="/account" className="inline-flex items-center px-4 py-2 rounded-lg bg-emerald-600 text-white hover:bg-emerald-700 font-medium transition shadow-sm">
                    👤 Account
                  </Link>
                  <Link href="/invoices/create" className="inline-flex items-center px-4 py-2 rounded-lg bg-emerald-700 text-white hover:bg-emerald-800 font-medium transition shadow-sm">
                    ➕ New Invoice
                  </Link>
                  <Link href="/invoices" className="inline-flex items-center px-4 py-2 rounded-lg bg-slate-700 text-emerald-100 hover:bg-slate-600 font-medium transition">
                    📄 Invoices
                  </Link>
                  <Link href="/api-keys" className="inline-flex items-center px-4 py-2 rounded-lg bg-slate-700 text-emerald-100 hover:bg-slate-600 font-medium transition">
                    🔑 API Keys
                  </Link>
                  <button 
                    onClick={() => {
                      localStorage.removeItem('token');
                      window.location.href = '/login';
                    }}
                    className="inline-flex items-center px-4 py-2 rounded-lg bg-red-700 text-white hover:bg-red-800 font-medium transition shadow-sm"
                  >
                    🚪 Logout
                  </button>
                </div>
              </div>
            </div>
          </header>

          <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          {/* Key Metrics */}
          <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
            <div className="bg-slate-800/80 backdrop-blur-sm rounded-lg shadow-lg border border-emerald-600/30 p-6 hover:shadow-emerald-500/20 hover:shadow-xl transition">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-emerald-300">Total Revenue</p>
                  <p className="text-3xl font-bold text-white mt-2">{stats?.total_amount ? `€${parseFloat(stats.total_amount).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}` : '—'}</p>
                </div>
                <div className="text-4xl opacity-20 text-emerald-400">💰</div>
              </div>
              <div className="mt-4 text-xs text-emerald-200/70">All time earnings</div>
            </div>

            <div className="bg-slate-800/80 backdrop-blur-sm rounded-lg shadow-lg border border-emerald-600/30 p-6 hover:shadow-emerald-500/20 hover:shadow-xl transition">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-emerald-300">Web2 Transactions</p>
                  <p className="text-3xl font-bold text-emerald-400 mt-2">{stats?.web2_count ?? '—'}</p>
                </div>
                <div className="text-4xl opacity-20 text-emerald-400">💳</div>
              </div>
              <div className="mt-4 text-xs text-emerald-200/70">Card & payment methods</div>
            </div>

            <div className="bg-slate-800/80 backdrop-blur-sm rounded-lg shadow-lg border border-emerald-600/30 p-6 hover:shadow-emerald-500/20 hover:shadow-xl transition">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-emerald-300">Web3 Transactions</p>
                  <p className="text-3xl font-bold text-purple-400 mt-2">{stats?.web3_count ?? '—'}</p>
                </div>
                <div className="text-4xl opacity-20 text-purple-400">🔗</div>
              </div>
              <div className="mt-4 text-xs text-emerald-200/70">Blockchain payments</div>
            </div>

            <div className="bg-slate-800/80 backdrop-blur-sm rounded-lg shadow-lg border border-emerald-600/30 p-6 hover:shadow-emerald-500/20 hover:shadow-xl transition">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-emerald-300">Active API Keys</p>
                  <p className="text-3xl font-bold text-cyan-400 mt-2">{apiKeys.length}</p>
                </div>
                <div className="text-4xl opacity-20 text-cyan-400">🔐</div>
              </div>
              <div className="mt-4 text-xs text-emerald-200/70">{apiKeys.filter((k: any) => k.mode === 'live').length} live keys</div>
            </div>
          </div>

          {/* Charts Section */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-8">
            <div className="lg:col-span-2 bg-slate-800/80 backdrop-blur-sm rounded-lg shadow-lg border border-emerald-600/30 p-6">
              <div className="mb-6">
                <h2 className="text-lg font-semibold text-white">Revenue Trend</h2>
                <p className="text-sm text-emerald-200/70">Transaction volume over time</p>
              </div>
              <RevenueChart data={revenueData.length ? revenueData : [{ date: '01', amount: 0 }]} />
            </div>

            <div className="bg-slate-800/80 backdrop-blur-sm rounded-lg shadow-lg border border-emerald-600/30 p-6">
              <div className="mb-6">
                <h2 className="text-lg font-semibold text-white">Payment Mix</h2>
                <p className="text-sm text-emerald-200/70">Web2 vs Web3 distribution</p>
              </div>
              <PaymentDonut data={donutData} />
            </div>
          </div>

          {/* VAT Section */}
          <div className="bg-slate-800/80 backdrop-blur-sm rounded-lg shadow-lg border border-emerald-600/30 p-6 mb-8">
            <div className="mb-6">
              <h2 className="text-lg font-semibold text-white">VAT Compliance</h2>
              <p className="text-sm text-emerald-200/70">Validate and check VAT numbers</p>
            </div>
            <VATChecker />
          </div>

          {/* Bottom Section */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            <div className="lg:col-span-2 bg-slate-800/80 backdrop-blur-sm rounded-lg shadow-lg border border-emerald-600/30 p-6">
              <div className="mb-6">
                <h2 className="text-lg font-semibold text-white">API Keys</h2>
                <p className="text-sm text-emerald-200/70">Manage your API credentials</p>
              </div>
              <ApiKeysList keys={apiKeys.map((k: any) => ({ id: k.id, key_type: k.type, masked: k.masked || k.id, created_at: k.created_at }))} onRevoke={handleRevoke} />
            </div>

            <div className="bg-slate-800/80 backdrop-blur-sm rounded-lg shadow-lg border border-emerald-600/30 p-6">
              <div className="mb-6">
                <h2 className="text-lg font-semibold text-white">Plugin Setup</h2>
                <p className="text-sm text-emerald-200/70">Integrate with your site</p>
              </div>
              <PluginSetup snippet={`<script src="/plugin.js"></script>`} />
            </div>
          </div>

          {/* Footer Info */}
          <div className="mt-8 p-4 bg-emerald-900/50 border border-emerald-600/30 rounded-lg backdrop-blur-sm">
            <p className="text-sm text-emerald-100">
              <span className="font-semibold">💡 Tip:</span> Use the API to automate invoice creation and payment tracking. Check out our documentation for integration examples.
            </p>
          </div>
        </main>
        </div>
      </div>
    </AuthGuard>
  );
}
