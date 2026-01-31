import { useEffect, useState } from 'react';
import { api } from '../lib/api';
import Link from 'next/link';

export default function Dashboard() {
  const [stats, setStats] = useState<any>(null);

  useEffect(() => {
    api('/merchant/usage')
      .then(setStats)
      .catch(console.error);
  }, []);

  return (
    <div className="p-8">
      <h1 className="text-3xl font-bold mb-6">Merchant Dashboard</h1>
      <div className="mb-4">
        <Link href="/api-keys" className="text-blue-600 hover:underline mr-4">API Keys</Link>
        <Link href="/plugin-setup" className="text-blue-600 hover:underline">Plugin Setup</Link>
      </div>
      {stats ? (
        <div className="grid grid-cols-2 gap-4">
          <div className="p-4 border rounded">
            <p className="text-gray-500">Invoices This Month</p>
            <p className="text-xl font-bold">{stats.invoices_this_month}</p>
          </div>
          <div className="p-4 border rounded">
            <p className="text-gray-500">API Calls</p>
            <p className="text-xl font-bold">{stats.api_calls}</p>
          </div>
          <div className="p-4 border rounded">
            <p className="text-gray-500">Web2 Usage</p>
            <p className="text-xl font-bold">{stats.web2_usage}</p>
          </div>
          <div className="p-4 border rounded">
            <p className="text-gray-500">Web3 Usage</p>
            <p className="text-xl font-bold">{stats.web3_usage}</p>
          </div>
          <div className="p-4 border rounded">
            <p className="text-gray-500">Errors</p>
            <p className="text-xl font-bold">{stats.errors}</p>
          </div>
        </div>
      ) : (
        <p>Loading stats...</p>
      )}
    </div>
  );
}
