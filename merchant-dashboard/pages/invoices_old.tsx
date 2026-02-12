import { useEffect, useState } from 'react';
import Link from 'next/link';
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
  const [invoices, setInvoices] = useState<Invoice[]>([]);
  const [loading, setLoading] = useState(true);
  const [downloadingId, setDownloadingId] = useState<string | null>(null);
  const [selectedInvoiceId, setSelectedInvoiceId] = useState<string | null>(null);
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

  const downloadCSV = () => {
    try {
      // Build CSV header
      const headers = ['Invoice #', 'Order #', 'Customer', 'Amount', 'VAT', 'Total', 'Payment System', 'Status', 'Created Date'];
      
      // Build CSV rows
      const rows = invoices.map(inv => [
        inv.invoice_number || inv.id,
        inv.order_number || '',
        inv.buyer_name || '',
        inv.subtotal || 0,
        inv.vat_amount || 0,
        inv.total || 0,
        inv.payment_system || 'web2',
        inv.status || 'unknown',
        inv.created_at || ''
      ]);

      // Create CSV content
      const csvContent = [
        headers.join(','),
        ...rows.map(row => row.map(cell => `"${cell}"`).join(','))
      ].join('\n');

      // Download CSV
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

  const downloadAllPDFs = async () => {
    try {
      setDownloadingAll(true);
      const token = typeof window !== 'undefined' ? localStorage.getItem('jwt') : null;
      
      // Download each invoice PDF with a small delay to avoid overwhelming the browser
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
            
            // Small delay between downloads to avoid overwhelming the browser
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

  return (
    <AuthGuard>
      <div className="min-h-screen bg-gray-50">
        <Header />
        
        <div className="max-w-7xl mx-auto px-4 py-8">
          <div className="mb-8">
            <h1 className="text-4xl font-bold text-gray-900 mb-2">Invoices</h1>
            <p className="text-gray-600">View and download your invoices</p>
          </div>

        {/* Navigation Links and Export Buttons */}
        <div className="mb-6 flex gap-3 justify-between items-center">
          <div className="flex gap-3">
            <Link href="/dashboard" className="px-4 py-2 rounded bg-gray-200 text-gray-800 hover:bg-gray-300 text-sm font-medium">
              Dashboard
            </Link>
            <Link href="/api-keys" className="px-4 py-2 rounded bg-gray-200 text-gray-800 hover:bg-gray-300 text-sm font-medium">
              API Keys
            </Link>
            <Link href="/invoices" className="px-4 py-2 rounded bg-green-600 text-white text-sm font-medium">
              Invoices
            </Link>
          </div>
          
          {invoices.length > 0 && (
            <div className="flex gap-2">
              <button
                onClick={downloadAllPDFs}
                disabled={downloadingAll}
                className="px-4 py-2 rounded bg-red-600 text-white hover:bg-red-700 disabled:opacity-60 disabled:cursor-not-allowed text-sm font-medium transition"
              >
                {downloadingAll ? '⏳ Exporting PDFs...' : '📄 Export PDF'}
              </button>
              <button
                onClick={downloadCSV}
                className="px-4 py-2 rounded bg-green-600 text-white hover:bg-green-700 text-sm font-medium"
              >
                📊 Export CSV
              </button>
            </div>
          )}
        </div>

        {loading ? (
          <div className="text-center py-12">
            <p className="text-gray-600">Loading invoices...</p>
          </div>
        ) : invoices.length === 0 ? (
            <div className="bg-white rounded-lg shadow p-8 text-center">
              <p className="text-gray-600 mb-4">No invoices found</p>
              <p className="text-sm text-gray-500">Invoices will appear here when they are created</p>
            </div>
          ) : (
            <div className="bg-white rounded-lg shadow overflow-hidden">
              <table className="min-w-full divide-y divide-gray-200">
                <thead className="bg-gray-100 border-b">
                  <tr>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-700 uppercase tracking-wider">Invoice #</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-700 uppercase tracking-wider">Order #</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-700 uppercase tracking-wider">Customer</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-700 uppercase tracking-wider">Amount</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-700 uppercase tracking-wider">Payment System</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-700 uppercase tracking-wider">Status</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-700 uppercase tracking-wider">Actions</th>
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                  {invoices.map((invoice) => (
                    <tr key={invoice.id} className="hover:bg-gray-50">
                      <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                        {invoice.invoice_number || invoice.id}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-600">
                        {invoice.order_number || '-'}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-600">
                        {invoice.buyer_name || '-'}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                        {invoice.total ? `$${(invoice.total).toFixed(2)}` : '-'}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm">
                        <span className={`inline-flex px-2 py-1 text-xs font-semibold rounded-full ${
                          invoice.payment_system === 'web3' 
                            ? 'bg-purple-100 text-purple-800' 
                            : 'bg-green-100 text-green-800'
                        }`}>
                          {invoice.payment_system || 'web2'}
                        </span>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm">
                        <span className={`inline-flex px-2 py-1 text-xs font-semibold rounded-full ${
                          invoice.status === 'paid'
                            ? 'bg-green-100 text-green-800'
                            : invoice.status === 'pending'
                            ? 'bg-yellow-100 text-yellow-800'
                            : 'bg-gray-100 text-gray-800'
                        }`}>
                          {invoice.status || 'unknown'}
                        </span>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm">
                        <div className="flex gap-2">
                          <button
                            onClick={() => downloadPDF(invoice.id)}
                            disabled={downloadingId === invoice.id}
                            title="Download this invoice as PDF"
                            className="inline-flex items-center px-3 py-2 rounded bg-red-600 text-white hover:bg-red-700 disabled:opacity-60 disabled:cursor-not-allowed text-sm font-semibold transition"
                          >
                            {downloadingId === invoice.id ? '⏳ PDF' : '📄 PDF'}
                          </button>
                          <button
                            onClick={() => {
                              const row = [
                                invoice.invoice_number || invoice.id,
                                invoice.order_number || '',
                                invoice.buyer_name || '',
                                invoice.subtotal || 0,
                                invoice.vat_amount || 0,
                                invoice.total || 0,
                                invoice.payment_system || 'web2',
                                invoice.status || 'unknown',
                                invoice.created_at || ''
                              ];
                              const csv = '"Invoice #","Order #","Customer","Subtotal","VAT","Total","Payment System","Status","Date"\n' + row.map(cell => `"${cell}"`).join(',');
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
                            title="Download this invoice as CSV"
                            className="inline-flex items-center px-3 py-2 rounded bg-green-600 text-white hover:bg-green-700 text-sm font-semibold transition"
                          >
                            📊 CSV
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>

              {/* Blockchain Transaction Info */}
              {invoices.some(inv => inv.blockchain_tx_id) && (
                <div className="px-6 py-4 bg-gray-50 border-t">
                  <p className="text-xs text-gray-600">
                    💡 Invoices with Web3 payment system include blockchain transaction IDs for verification
                  </p>
                </div>
              )}
            </div>
          )}

          {/* Invoice Stats */}
          {invoices.length > 0 && (
            <div className="mt-8 grid grid-cols-1 md:grid-cols-3 gap-4">
              <div className="bg-white rounded-lg shadow p-6">
                <p className="text-gray-600 text-sm">Total Invoices</p>
                <p className="text-3xl font-bold text-gray-900 mt-2">{invoices.length}</p>
              </div>
              <div className="bg-white rounded-lg shadow p-6">
                <p className="text-gray-600 text-sm">Web3 Invoices</p>
                <p className="text-3xl font-bold text-purple-600 mt-2">
                  {invoices.filter(i => i.payment_system === 'web3').length}
                </p>
              </div>
              <div className="bg-white rounded-lg shadow p-6">
                <p className="text-gray-600 text-sm">Total Amount</p>
                <p className="text-3xl font-bold text-green-600 mt-2">
                  ${invoices.reduce((sum, i) => sum + (i.total || 0), 0).toFixed(2)}
                </p>
              </div>
            </div>
          )}
        </div>
      </div>
    </AuthGuard>
  );
}
