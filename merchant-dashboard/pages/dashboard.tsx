import { useEffect, useState } from 'react';
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

  useEffect(() => {
    let mounted = true;

    const fetchUsage = async () => {
      setLoading(true);
      try {
        const [usage, keys] = await Promise.all([
          api.protectedApi('/merchant/usage'),
          api.protectedApi('/api-keys'),
        ]);
        if (!mounted) return;
        setStats(usage);
        setApiKeys(keys || []);
      } catch (e) {
        console.error(e);
      } finally {
        if (mounted) setLoading(false);
      }
    };

    fetchUsage();
    const interval = setInterval(fetchUsage, 3000);
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

  // placeholder sample data if stats absent
  const revenueData = (stats?.revenue || []).map((r: any) => ({ date: r.date, amount: r.amount }));
  const donutData = [
    { name: 'Web2', value: stats?.web2_total || 0 },
    { name: 'Web3', value: stats?.web3_total || 0 },
  ];

  return (
    <AuthGuard>
      <div className="container py-8">
        <div className="flex items-center justify-between mb-6">
          <h1 className="text-2xl font-bold">Dashboard — Invoicing Merchant</h1>
        </div>

        <div className="grid grid-cols-4 gap-4 mb-6">
          <div className="card">
            <p className="text-sm text-gray-500">Total Revenue</p>
            <p className="text-2xl font-bold">{stats?.total_amount ?? '—'}</p>
          </div>
          <div className="card">
            <p className="text-sm text-gray-500">Web2 Payments</p>
            <p className="text-2xl font-bold">{stats?.web2_count ?? '—'}</p>
          </div>
          <div className="card">
            <p className="text-sm text-gray-500">Web3 Payments</p>
            <p className="text-2xl font-bold">{stats?.web3_count ?? '—'}</p>
          </div>
          <div className="card">
            <p className="text-sm text-gray-500">API Keys</p>
            <p className="text-2xl font-bold">{apiKeys.length}</p>
          </div>
        </div>

        <div className="grid grid-cols-3 gap-4 mb-6">
          <div className="col-span-2">
            <RevenueChart data={revenueData.length ? revenueData : [{ date: '01', amount: 0 }]} />
          </div>
          <div>
            <PaymentDonut data={donutData} />
          </div>
        </div>

        <div className="grid grid-cols-3 gap-4 mb-6">
          <div className="col-span-3">
            <VATChecker />
          </div>
        </div>

        <div className="grid grid-cols-3 gap-4">
          <div className="col-span-2">
            <ApiKeysList keys={apiKeys.map((k: any) => ({ id: k.id, key_type: k.type, masked: k.masked || k.id, created_at: k.created_at }))} onRevoke={handleRevoke} />
          </div>
          <div>
            <PluginSetup snippet={`<script src="/plugin.js"></script>`} />
          </div>
        </div>
      </div>
    </AuthGuard>
  );
}
