import { useEffect, useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/router';
import api from '../lib/api';
import AuthGuard from '../components/AuthGuard';
import Header from '../components/Header';

interface Invoice {
  id: string;
  invoice_number?: string;
  order_number?: string;
  seller_name?: string;
  buyer_name?: string;
  subtotal?: number;
  vat_amount?: number;
  total?: number;
  payment_system?: string;
  blockchain_tx_id?: string;
  pdf_url?: string;
  created_at?: string;
  status?: string;
  mode?: string;
}

export default function Invoices() {
  const router = useRouter();
  const [invoices, setInvoices] = useState<Invoice[]>([]);
  const [loading, setLoading] = useState(true);
  const [downloadingId, setDownloadingId] = useState<string | null>(null);
  const [downloadingAll, setDownloadingAll] = useState(false);

  useEffect(() => {
    const fetchInvoices = async () => {
      try {
        setLoading(true);
        const data = await api.protectedApi('/invoices');
        setInvoices(Array.isArray(data) ? data : []);
      } catch (err) {
        console.error('Failed to load invoices:', err);
        setInvoices([]);
      } finally {
        setLoading(false);
      }
    };
    fetchInvoices();
  }, []);

  const downloadPDF = async (invoiceId: string) => {
    try {
      setDownloadingId(invoiceId);
      const token = typeof window !== 'undefined' ? localStorage.getItem('jwt') : null;
      const pdfUrl = `https://api.apiblockchain.io/invoices/${invoiceId}/pdf`;
      
      const response = await fetch(pdfUrl, {
        headers: token ? { 'Authorization': `Bearer ${token}` } : {},
      });
      
      if (!response.ok) throw new Error('Failed to download PDF');
      
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `invoice-${invoiceId}.pdf`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);
    } catch (err) {
      console.error('Failed to download PDF:', err);
      alert('Failed to download invoice PDF');
    } finally {
      setDownloadingId(null);
    }
  };

  const downloadAllPDFs = async () => {
    try {
      setDownloadingAll(true);
      const token = typeof window !== 'undefined' ? localStorage.getItem('jwt') : null;
      
      for (let i = 0; i < invoices.length; i++) {
        const invoiceId = invoices[i].id;
        const pdfUrl = `https://api.apiblockchain.io/invoices/${invoiceId}/pdf`;
        
        try {
          const response = await fetch(pdfUrl, {
            headers: token ? { 'Authorization': `Bearer ${token}` } : {},
          });
          
          if (response.ok) {
            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const link = document.createElement('a');
            link.href = url;
            link.download = `invoice-${invoices[i].invoice_number || invoiceId}.pdf`;
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
            window.URL.revokeObjectURL(url);
            
            if (i < invoices.length - 1) {
              await new Promise(resolve => setTimeout(resolve, 300));
            }
          }
        } catch (err) {
          console.error(`Failed to download invoice ${invoiceId}:`, err);
        }
      }
      
      alert(`Downloaded ${invoices.length} invoice PDFs`);
    } catch (err) {
      console.error('Failed to download PDFs:', err);
      alert('Failed to export invoices as PDFs');
    } finally {
      setDownloadingAll(false);
    }
  };

  const downloadCSV = () => {
    try {
      const headers = ['Invoice #', 'Customer', 'Subtotal', 'VAT', 'Total', 'Payment System', 'Status', 'Date'];
      
      const rows = invoices.map(inv => [
        inv.invoice_number || inv.id,
        inv.buyer_name || '',
        inv.subtotal || 0,
        inv.vat_amount || 0,
        inv.total || 0,
        inv.payment_system || 'web2',
        inv.status || 'unknown',
        inv.created_at || ''
      ]);

      const csvContent = [
        headers.join(','),
        ...rows.map(row => row.map(cell => `"${cell}"`).join(','))
      ].join('\n');

      const blob = new Blob([csvContent], { type: 'text/csv' });
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `invoices-${new Date().toISOString().split('T')[0]}.csv`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);
    } catch (err) {
      console.error('Failed to download CSV:', err);
      alert('Failed to export invoices as CSV');
    }
  };

  return (
    <AuthGuard>
      <div className="min-h-screen bg-gradient-to-br from-gray-50 to-gray-100">
        <Header />
        
        <div className="max-w-7xl mx-auto px-4 py-8">
          {/* Page Header */}
          <div className="mb-8 flex items-center justify-between">
            <div>
              <h1 className="text-4xl font-bold text-gray-900 mb-2">Invoices</h1>
              <p className="text-gray-600">Manage, view, and download your merchant invoices</p>
            </div>
            <div className="flex gap-3">
              <Link href="/invoices/create" className="px-4 py-2 rounded bg-green-600 text-white hover:bg-green-700 text-sm font-medium transition">
                ➕ Create Invoice
              </Link>
              <Link href="/dashboard" className="px-4 py-2 rounded bg-gray-600 text-white hover:bg-gray-700 text-sm font-medium transition">
                Dashboard
              </Link>
            </div>
          </div>

          {loading ? (
            <div className="text-center py-16">
              <p className="text-gray-600 text-lg">Loading invoices...</p>
            </div>
          ) : invoices.length === 0 ? (
            <div className="bg-white rounded-lg shadow p-12 text-center">
              <p className="text-gray-600 text-lg mb-4">No invoices found</p>
              <p className="text-sm text-gray-500">Invoices will appear here when they are created</p>
            </div>
          ) : (
            <>
              {/* Statistics Cards */}
              <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8">
                <div className="bg-white rounded-lg shadow p-6 border-l-4 border-green-600 hover:shadow-lg transition">
                  <p className="text-gray-600 text-sm font-medium mb-2">Total Invoices</p>
                  <p className="text-3xl font-bold text-gray-900">{invoices.length}</p>
                </div>
                <div className="bg-white rounded-lg shadow p-6 border-l-4 border-green-600 hover:shadow-lg transition">
                  <p className="text-gray-600 text-sm font-medium mb-2">Total Revenue</p>
                  <p className="text-3xl font-bold text-gray-900">${invoices.reduce((sum, inv) => sum + (inv.total || 0), 0).toFixed(2)}</p>
                </div>
                <div className="bg-white rounded-lg shadow p-6 border-l-4 border-purple-600 hover:shadow-lg transition">
                  <p className="text-gray-600 text-sm font-medium mb-2">Web3 Invoices</p>
                  <p className="text-3xl font-bold text-gray-900">{invoices.filter(inv => inv.payment_system === 'web3').length}</p>
                </div>
                <div className="bg-white rounded-lg shadow p-6 border-l-4 border-yellow-600 hover:shadow-lg transition">
                  <p className="text-gray-600 text-sm font-medium mb-2">Pending Payment</p>
                  <p className="text-3xl font-bold text-gray-900">{invoices.filter(inv => inv.status === 'pending').length}</p>
                </div>
              </div>

              {/* Export Buttons */}
              <div className="mb-6 flex gap-3 justify-end">
                <button
                  onClick={downloadAllPDFs}
                  disabled={downloadingAll}
                  className="inline-flex items-center px-6 py-3 rounded-lg bg-red-600 text-white hover:bg-red-700 disabled:opacity-60 disabled:cursor-not-allowed font-semibold transition shadow hover:shadow-lg"
                >
                  {downloadingAll ? '⏳ Exporting PDFs...' : '📄 Export All as PDF'}
                </button>
                <button
                  onClick={downloadCSV}
                  className="inline-flex items-center px-6 py-3 rounded-lg bg-green-600 text-white hover:bg-green-700 font-semibold transition shadow hover:shadow-lg"
                >
                  📊 Export as CSV
                </button>
              </div>

              {/* Invoices Table */}
              <div className="bg-white rounded-lg shadow overflow-hidden">
                <div className="overflow-x-auto">
                  <table className="w-full">
                    <thead className="bg-gradient-to-r from-gray-50 to-gray-100 border-b-2 border-gray-200">
                      <tr>
                        <th className="px-6 py-4 text-left text-xs font-bold text-gray-700 uppercase tracking-wider">Invoice #</th>
                        <th className="px-6 py-4 text-left text-xs font-bold text-gray-700 uppercase tracking-wider">Customer</th>
                        <th className="px-6 py-4 text-right text-xs font-bold text-gray-700 uppercase tracking-wider">Subtotal</th>
                        <th className="px-6 py-4 text-right text-xs font-bold text-gray-700 uppercase tracking-wider">VAT</th>
                        <th className="px-6 py-4 text-right text-xs font-bold text-gray-700 uppercase tracking-wider">Total</th>
                        <th className="px-6 py-4 text-left text-xs font-bold text-gray-700 uppercase tracking-wider">Payment</th>
                        <th className="px-6 py-4 text-left text-xs font-bold text-gray-700 uppercase tracking-wider">Status</th>
                        <th className="px-6 py-4 text-left text-xs font-bold text-gray-700 uppercase tracking-wider">Date</th>
                        <th className="px-6 py-4 text-center text-xs font-bold text-gray-700 uppercase tracking-wider">Actions</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-200">
                      {invoices.map((invoice, idx) => (
                        <tr key={invoice.id} className={`hover:bg-green-50 transition cursor-pointer ${idx % 2 === 0 ? 'bg-white' : 'bg-gray-50'}`} onClick={() => router.push(`/invoices/${invoice.id}`)}>
                          <td className="px-6 py-4 whitespace-nowrap">
                            <Link href={`/invoices/${invoice.id}`} className="text-sm font-bold text-green-600 hover:text-green-800 hover:underline">
                              {invoice.invoice_number || invoice.id}
                            </Link>
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap">
                            <span className="text-sm text-gray-700">{invoice.buyer_name || '-'}</span>
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap text-right">
                            <span className="text-sm text-gray-700">${(invoice.subtotal || 0).toFixed(2)}</span>
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap text-right">
                            <span className="text-sm text-gray-700">${(invoice.vat_amount || 0).toFixed(2)}</span>
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap text-right">
                            <span className="text-sm font-bold text-gray-900">${(invoice.total || 0).toFixed(2)}</span>
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap">
                            <span className={`inline-flex items-center px-3 py-1 text-xs font-semibold rounded-full ${
                              invoice.payment_system === 'web3' 
                                ? 'bg-purple-100 text-purple-800' 
                                : 'bg-green-100 text-green-800'
                            }`}>
                              {invoice.payment_system === 'web3' ? '🔗 Web3' : '💳 Web2'}
                            </span>
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap">
                            <span className={`inline-flex items-center px-3 py-1 text-xs font-semibold rounded-full ${
                              invoice.status === 'paid'
                                ? 'bg-green-100 text-green-800'
                                : invoice.status === 'pending'
                                ? 'bg-yellow-100 text-yellow-800'
                                : 'bg-gray-100 text-gray-800'
                            }`}>
                              {invoice.status === 'paid' ? '✅ Paid' : invoice.status === 'pending' ? '⏳ Pending' : invoice.status}
                            </span>
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap">
                            <span className="text-sm text-gray-600 font-medium">{invoice.created_at ? new Date(invoice.created_at).toLocaleDateString('en-US', { year: 'numeric', month: 'short', day: 'numeric' }) : '-'}</span>
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap">
                            <div className="flex gap-2 justify-center">
                              <button
                                onClick={() => downloadPDF(invoice.id)}
                                disabled={downloadingId === invoice.id}
                                title="Download invoice as PDF"
                                className="inline-flex items-center justify-center px-3 py-2 rounded-lg bg-red-600 text-white hover:bg-red-700 disabled:opacity-60 disabled:cursor-not-allowed font-bold transition hover:shadow-md w-10 h-10"
                              >
                                {downloadingId === invoice.id ? '⏳' : '📄'}
                              </button>
                              <button
                                onClick={() => {
                                  const row = [
                                    invoice.invoice_number || invoice.id,
                                    invoice.buyer_name || '',
                                    invoice.subtotal || 0,
                                    invoice.vat_amount || 0,
                                    invoice.total || 0,
                                    invoice.payment_system || 'web2',
                                    invoice.status || 'unknown',
                                    invoice.created_at || ''
                                  ];
                                  const csv = '"Invoice #","Customer","Subtotal","VAT","Total","Payment System","Status","Date"\n' + row.map(cell => `"${cell}"`).join(',');
                                  const blob = new Blob([csv], { type: 'text/csv' });
                                  const url = window.URL.createObjectURL(blob);
                                  const link = document.createElement('a');
                                  link.href = url;
                                  link.download = `invoice-${invoice.id}.csv`;
                                  document.body.appendChild(link);
                                  link.click();
                                  document.body.removeChild(link);
                                  window.URL.revokeObjectURL(url);
                                }}
                                title="Download invoice as CSV"
                                className="inline-flex items-center justify-center px-3 py-2 rounded-lg bg-green-600 text-white hover:bg-green-700 font-bold transition hover:shadow-md w-10 h-10"
                              >
                                📊
                              </button>
                            </div>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>

                {/* Footer Info */}
                {invoices.some(inv => inv.blockchain_tx_id) && (
                  <div className="px-6 py-4 bg-green-50 border-t border-green-200">
                    <p className="text-sm text-green-800 flex items-center gap-2">
                      <span>ℹ️</span>
                      <span>Web3 invoices include blockchain transaction IDs for verification</span>
                    </p>
                  </div>
                )}
              </div>
            </>
          )}
        </div>
      </div>
    </AuthGuard>
  );
}
