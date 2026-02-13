import { useEffect, useState } from 'react';
import { useRouter } from 'next/router';
import Link from 'next/link';
import api from '../../lib/api';
import AuthGuard from '../../components/AuthGuard';

interface Invoice {
  id: string;
  invoice_number?: string;
  order_number?: string;
  seller_name?: string;
  buyer_name?: string;
  buyer_email?: string;
  buyer_address?: string;
  buyer_country?: string;
  buyer_vat?: string;
  buyer_type?: string;
  seller_address?: string;
  subtotal?: number;
  vat_amount?: number;
  vat_rate?: number;
  total?: number;
  payment_system?: string;
  blockchain_tx_id?: string;
  pdf_url?: string;
  created_at?: string;
  status?: string;
  mode?: string;
  due_date?: string;
  items?: any[];
  notes?: string;
}

export default function InvoiceDetail() {
  const router = useRouter();
  const { id } = router.query;
  const [invoice, setInvoice] = useState<Invoice | null>(null);
  const [loading, setLoading] = useState(true);
  const [downloading, setDownloading] = useState(false);
  const [isEditMode, setIsEditMode] = useState(false);
  const [editData, setEditData] = useState<any>(null);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const toNumber = (value: any) => {
    const n = Number(value);
    return Number.isFinite(n) ? n : 0;
  };

  const formatCurrency = (value: any) =>
    new Intl.NumberFormat('en-US', { style: 'currency', currency: 'EUR' }).format(toNumber(value));

  useEffect(() => {
    if (!id) return;

    const fetchInvoice = async () => {
      try {
        setLoading(true);
        const data = await api.protectedApi(`/invoices/${id}`);
        setInvoice(data);
      } catch (err) {
        console.error('Failed to load invoice:', err);
      } finally {
        setLoading(false);
      }
    };

    fetchInvoice();
  }, [id]);

  const downloadPDF = async () => {
    if (!id) return;
    try {
      setDownloading(true);
      const token = typeof window !== 'undefined' ? localStorage.getItem('jwt') : null;
      const pdfUrl = `https://api.apiblockchain.io/invoices/${id}/pdf`;
      
      const response = await fetch(pdfUrl, {
        headers: token ? { 'Authorization': `Bearer ${token}` } : {},
      });
      
      if (!response.ok) throw new Error('Failed to download PDF');
      
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `invoice-${invoice?.invoice_number || id}.pdf`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);
    } catch (err) {
      console.error('Failed to download PDF:', err);
      alert('Failed to download invoice PDF');
    } finally {
      setDownloading(false);
    }
  };

  const handleEdit = () => {
    setEditData({
      status: invoice?.status || 'draft',
      due_date: invoice?.due_date || '',
      buyer_name: invoice?.buyer_name || '',
      buyer_email: invoice?.buyer_email || '',
      buyer_address: invoice?.buyer_address || '',
      buyer_country: invoice?.buyer_country || '',
      buyer_vat: invoice?.buyer_vat || '',
      buyer_type: invoice?.buyer_type || 'B2C',
      notes: invoice?.notes || '',
      vat_rate: invoice?.vat_rate || 21,
    });
    setIsEditMode(true);
    setError(null);
  };

  const handleSave = async () => {
    if (!id || !invoice) return;
    try {
      setSaving(true);
      setError(null);
      const token = typeof window !== 'undefined' ? localStorage.getItem('jwt') : null;
      const response = await fetch(`https://api.apiblockchain.io/invoices/${id}`, {
        method: 'PATCH',
        headers: {
          'Content-Type': 'application/json',
          ...(token ? { 'Authorization': `Bearer ${token}` } : {}),
        },
        body: JSON.stringify(editData),
      });

      if (!response.ok) {
        const errData = await response.json();
        throw new Error(errData.detail || 'Failed to update invoice');
      }

      const updated = await response.json();
      setInvoice(updated);
      setIsEditMode(false);
      setEditData(null);
      alert('Invoice updated successfully');
    } catch (err: any) {
      console.error('Failed to save invoice:', err);
      setError(err.message || 'Failed to save invoice');
    } finally {
      setSaving(false);
    }
  };

  const handleCancel = () => {
    setIsEditMode(false);
    setEditData(null);
    setError(null);
  };

  return (
    <AuthGuard>
      <div className="min-h-screen bg-gradient-to-br from-gray-50 to-gray-100">        
        <div className="max-w-4xl mx-auto px-4 py-8">
          {/* Back Button */}
          <div className="mb-6">
            <Link href="/invoices" className="inline-flex items-center px-4 py-2 rounded-lg bg-gray-600 text-white hover:bg-gray-700 font-medium transition">
              ← Back to Invoices
            </Link>
          </div>

          {loading ? (
            <div className="text-center py-16">
              <p className="text-gray-600 text-lg">Loading invoice...</p>
            </div>
          ) : !invoice ? (
            <div className="bg-white rounded-lg shadow p-8 text-center">
              <p className="text-gray-600 text-lg">Invoice not found</p>
            </div>
          ) : isEditMode && editData ? (
            <div className="bg-white rounded-lg shadow p-8">
              <h2 className="text-2xl font-bold text-gray-900 mb-6">Edit Invoice</h2>
              
              {error && (
                <div className="mb-6 p-4 bg-red-100 border border-red-400 text-red-700 rounded">
                  {error}
                </div>
              )}

              <div className="grid grid-cols-2 gap-6 mb-6">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">Status</label>
                  <select
                    value={editData.status}
                    onChange={(e) => setEditData({ ...editData, status: e.target.value })}
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-600 focus:border-transparent"
                  >
                    <option value="draft">Draft</option>
                    <option value="sent">Sent</option>
                    <option value="paid">Paid</option>
                    <option value="overdue">Overdue</option>
                    <option value="cancelled">Cancelled</option>
                  </select>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">Due Date</label>
                  <input
                    type="date"
                    value={editData.due_date}
                    onChange={(e) => setEditData({ ...editData, due_date: e.target.value })}
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-600 focus:border-transparent"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">Buyer Name</label>
                  <input
                    type="text"
                    value={editData.buyer_name}
                    onChange={(e) => setEditData({ ...editData, buyer_name: e.target.value })}
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-600 focus:border-transparent"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">Buyer Email</label>
                  <input
                    type="email"
                    value={editData.buyer_email}
                    onChange={(e) => setEditData({ ...editData, buyer_email: e.target.value })}
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-600 focus:border-transparent"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">Buyer Country</label>
                  <input
                    type="text"
                    value={editData.buyer_country}
                    onChange={(e) => setEditData({ ...editData, buyer_country: e.target.value })}
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-600 focus:border-transparent"
                    placeholder="e.g., NL, DE, FR"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">Buyer VAT</label>
                  <input
                    type="text"
                    value={editData.buyer_vat}
                    onChange={(e) => setEditData({ ...editData, buyer_vat: e.target.value })}
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-600 focus:border-transparent"
                  />
                </div>
              </div>

              <div className="mb-6">
                <label className="block text-sm font-medium text-gray-700 mb-2">Notes</label>
                <textarea
                  value={editData.notes}
                  onChange={(e) => setEditData({ ...editData, notes: e.target.value })}
                  rows={4}
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-600 focus:border-transparent"
                />
              </div>

              <div className="flex gap-4 justify-center">
                <button
                  onClick={handleSave}
                  disabled={saving}
                  className="inline-flex items-center px-8 py-3 rounded-lg bg-green-600 text-white hover:bg-green-700 disabled:opacity-60 disabled:cursor-not-allowed font-bold transition shadow hover:shadow-lg"
                >
                  {saving ? '💾 Saving...' : '💾 Save Changes'}
                </button>
                <button
                  onClick={handleCancel}
                  disabled={saving}
                  className="inline-flex items-center px-8 py-3 rounded-lg bg-gray-600 text-white hover:bg-gray-700 disabled:opacity-60 disabled:cursor-not-allowed font-bold transition shadow hover:shadow-lg"
                >
                  ✕ Cancel
                </button>
              </div>
            </div>
          ) : (
            <div className="space-y-6">
              {/* Header Section */}
              <div className="bg-white rounded-lg shadow p-8">
                <div className="flex justify-between items-start mb-6">
                  <div className="pr-8">
                    <h1 className="text-4xl font-bold text-gray-900 mb-4">Invoice</h1>
                    <p className="text-2xl font-bold text-green-600">{invoice.invoice_number || invoice.id}</p>
                  </div>
                  <div className="text-right">
                    <span className={`inline-flex items-center px-4 py-2 text-lg font-bold rounded-full ${
                      invoice.status === 'paid'
                        ? 'bg-green-100 text-green-800'
                        : invoice.status === 'pending'
                        ? 'bg-yellow-100 text-yellow-800'
                        : 'bg-gray-100 text-gray-800'
                    }`}>
                      {invoice.status === 'paid' ? '✅ PAID' : invoice.status === 'pending' ? '⏳ PENDING' : invoice.status}
                    </span>
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-8 pt-6 border-t border-gray-200">
                  {/* Invoice Info */}
                  <div>
                    <h3 className="text-sm font-bold text-gray-700 uppercase tracking-wider mb-4">Invoice Information</h3>
                    <div className="space-y-3">
                      <div>
                        <p className="text-xs text-gray-600 uppercase font-medium">Invoice Number</p>
                        <p className="text-lg font-semibold text-gray-900">{invoice.invoice_number || invoice.id}</p>
                      </div>
                      {invoice.order_number && (
                        <div>
                          <p className="text-xs text-gray-600 uppercase font-medium">Order Number</p>
                          <p className="text-lg font-semibold text-gray-900">{invoice.order_number}</p>
                        </div>
                      )}
                      <div>
                        <p className="text-xs text-gray-600 uppercase font-medium">Issue Date</p>
                        <p className="text-lg font-semibold text-gray-900">
                          {invoice.created_at ? new Date(invoice.created_at).toLocaleDateString('en-US', { year: 'numeric', month: 'long', day: 'numeric' }) : '-'}
                        </p>
                      </div>
                      {invoice.due_date && (
                        <div>
                          <p className="text-xs text-gray-600 uppercase font-medium">Due Date</p>
                          <p className="text-lg font-semibold text-gray-900">
                            {new Date(invoice.due_date).toLocaleDateString('en-US', { year: 'numeric', month: 'long', day: 'numeric' })}
                          </p>
                        </div>
                      )}
                    </div>
                  </div>

                  {/* Payment Info */}
                  <div>
                    <h3 className="text-sm font-bold text-gray-700 uppercase tracking-wider mb-4">Payment Information</h3>
                    <div className="space-y-3">
                      <div>
                        <p className="text-xs text-gray-600 uppercase font-medium">Payment System</p>
                        <p className="text-lg font-semibold">
                          <span className={`inline-flex items-center px-3 py-1 rounded-full text-sm font-bold ${
                            invoice.payment_system === 'web3' 
                              ? 'bg-purple-100 text-purple-800' 
                              : 'bg-green-100 text-green-800'
                          }`}>
                            {invoice.payment_system === 'web3' ? '🔗 Blockchain (Web3)' : '💳 Traditional (Web2)'}
                          </span>
                        </p>
                      </div>
                      {invoice.blockchain_tx_id && (
                        <div>
                          <p className="text-xs text-gray-600 uppercase font-medium">Blockchain TX ID</p>
                          <p className="text-sm font-mono bg-gray-100 p-2 rounded break-all text-gray-800">{invoice.blockchain_tx_id}</p>
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              </div>

              {/* Parties Section */}
              <div className="grid grid-cols-2 gap-6">
                {/* From */}
                <div className="bg-white rounded-lg shadow p-8">
                  <h3 className="text-sm font-bold text-gray-700 uppercase tracking-wider mb-6 pb-4 border-b">From (Seller)</h3>
                  <div className="space-y-2">
                    <div>
                      <p className="text-xs text-gray-600 uppercase font-medium">Seller Name</p>
                      <p className="text-lg font-semibold text-gray-900">{invoice.seller_name || 'APIBlockchain'}</p>
                    </div>
                    {invoice.seller_address && (
                      <div>
                        <p className="text-xs text-gray-600 uppercase font-medium mt-3">Address</p>
                        <p className="text-sm text-gray-700 whitespace-pre-wrap">{invoice.seller_address}</p>
                      </div>
                    )}
                  </div>
                </div>

                {/* To */}
                <div className="bg-white rounded-lg shadow p-8">
                  <h3 className="text-sm font-bold text-gray-700 uppercase tracking-wider mb-6 pb-4 border-b">Bill To (Customer)</h3>
                  <div className="space-y-2">
                    <div>
                      <p className="text-xs text-gray-600 uppercase font-medium">Customer Name</p>
                      <p className="text-lg font-semibold text-gray-900">{invoice.buyer_name || '-'}</p>
                    </div>
                    {invoice.buyer_email && (
                      <div>
                        <p className="text-xs text-gray-600 uppercase font-medium mt-3">Email</p>
                        <p className="text-sm text-green-600">{invoice.buyer_email}</p>
                      </div>
                    )}
                    {invoice.buyer_address && (
                      <div>
                        <p className="text-xs text-gray-600 uppercase font-medium mt-3">Address</p>
                        <p className="text-sm text-gray-700 whitespace-pre-wrap">{invoice.buyer_address}</p>
                      </div>
                    )}
                  </div>
                </div>
              </div>

              {/* Items Section */}
              <div className="bg-white rounded-lg shadow overflow-hidden">
                <div className="px-8 py-6 bg-gradient-to-r from-gray-50 to-gray-100 border-b">
                  <h3 className="text-sm font-bold text-gray-700 uppercase tracking-wider">Invoice Items</h3>
                </div>
                <div className="overflow-x-auto">
                  <table className="w-full">
                    <thead className="bg-gray-50 border-b">
                      <tr>
                        <th className="px-8 py-4 text-left text-xs font-bold text-gray-700 uppercase tracking-wider">Description</th>
                        <th className="px-8 py-4 text-right text-xs font-bold text-gray-700 uppercase tracking-wider">Quantity</th>
                        <th className="px-8 py-4 text-right text-xs font-bold text-gray-700 uppercase tracking-wider">Unit Price</th>
                        <th className="px-8 py-4 text-right text-xs font-bold text-gray-700 uppercase tracking-wider">Amount</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y">
                      {invoice.items && invoice.items.length > 0 ? (
                        invoice.items.map((item, idx) => (
                          <tr key={idx} className={idx % 2 === 0 ? 'bg-white' : 'bg-gray-50'}>
                            <td className="px-8 py-4 text-sm text-gray-900">{item.description || item.name || '-'}</td>
                            {(() => {
                              const qty = toNumber(item.quantity ?? 1);
                              const unitPrice = toNumber(item.unit_price ?? item.price ?? 0);
                              const amount = item.amount ?? qty * unitPrice;
                              return (
                                <>
                                  <td className="px-8 py-4 text-sm text-right text-gray-900">{qty}</td>
                                  <td className="px-8 py-4 text-sm text-right text-gray-900">{formatCurrency(unitPrice)}</td>
                                  <td className="px-8 py-4 text-sm text-right font-semibold text-gray-900">{formatCurrency(amount)}</td>
                                </>
                              );
                            })()}
                          </tr>
                        ))
                      ) : (
                        <tr>
                          <td colSpan={4} className="px-8 py-6 text-center text-gray-600">
                            No individual items listed
                          </td>
                        </tr>
                      )}
                    </tbody>
                  </table>
                </div>
              </div>

              {/* Totals Section */}
              <div className="bg-white rounded-lg shadow p-8">
                <div className="flex justify-end max-w-md ml-auto">
                  <div className="w-full space-y-4">
                    <div className="flex justify-between items-center pb-4 border-b">
                      <span className="text-gray-700 font-medium">Subtotal</span>
                      <span className="text-lg font-semibold text-gray-900">{formatCurrency(invoice.subtotal)}</span>
                    </div>
                    <div className="flex justify-between items-center pb-4 border-b">
                      <span className="text-gray-700 font-medium">VAT / Tax</span>
                      <span className="text-lg font-semibold text-gray-900">{formatCurrency(invoice.vat_amount)}</span>
                    </div>
                    <div className="flex justify-between items-center pt-4 bg-gradient-to-r from-green-50 to-green-100 p-4 rounded-lg">
                      <span className="text-lg font-bold text-gray-900">Total Due</span>
                      <span className="text-3xl font-bold text-green-600">{formatCurrency(invoice.total)}</span>
                    </div>
                  </div>
                </div>
              </div>

              {/* Notes Section */}
              {invoice.notes && (
                <div className="bg-white rounded-lg shadow p-8">
                  <h3 className="text-sm font-bold text-gray-700 uppercase tracking-wider mb-4 pb-4 border-b">Notes</h3>
                  <p className="text-gray-700 whitespace-pre-wrap">{invoice.notes}</p>
                </div>
              )}

              {/* Additional Info */}
              <div className="bg-green-50 rounded-lg shadow p-8 border-l-4 border-green-600">
                <h3 className="text-sm font-bold text-green-700 uppercase tracking-wider mb-4">Additional Information</h3>
                <div className="grid grid-cols-2 gap-6">
                  <div>
                    <p className="text-xs text-green-600 uppercase font-medium mb-2">Invoice Status</p>
                    <p className="text-lg font-semibold text-gray-900 capitalize">{invoice.status || 'Unknown'}</p>
                  </div>
                  <div>
                    <p className="text-xs text-green-600 uppercase font-medium mb-2">Mode</p>
                    <p className="text-lg font-semibold text-gray-900 capitalize">{invoice.mode || 'Production'}</p>
                  </div>
                </div>
              </div>

              {/* Action Buttons */}
              <div className="flex gap-4 justify-center flex-wrap">
                <Link href="/dashboard" className="inline-flex items-center px-8 py-3 rounded-lg bg-green-600 text-white hover:bg-green-700 font-bold transition shadow hover:shadow-lg">
                  🏠 Dashboard
                </Link>
                <button
                  onClick={handleEdit}
                  className="inline-flex items-center px-8 py-3 rounded-lg bg-blue-600 text-white hover:bg-blue-700 font-bold transition shadow hover:shadow-lg"
                >
                  ✏️ Edit Invoice
                </button>
                <button
                  onClick={downloadPDF}
                  disabled={downloading}
                  className="inline-flex items-center px-8 py-3 rounded-lg bg-red-600 text-white hover:bg-red-700 disabled:opacity-60 disabled:cursor-not-allowed font-bold transition shadow hover:shadow-lg"
                >
                  {downloading ? '⏳ Downloading PDF...' : '📄 Download as PDF'}
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
                  className="inline-flex items-center px-8 py-3 rounded-lg bg-green-600 text-white hover:bg-green-700 font-bold transition shadow hover:shadow-lg"
                >
                  📊 Download as CSV
                </button>
              </div>

              {/* Raw Invoice Data - Debug/Reference */}
              <div className="bg-gray-50 rounded-lg shadow p-8 border border-gray-300">
                <h3 className="text-sm font-bold text-gray-700 uppercase tracking-wider mb-4 pb-4 border-b">Complete Invoice Data</h3>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  <div>
                    <h4 className="font-semibold text-gray-900 mb-3">Basic Information</h4>
                    <div className="space-y-2 text-sm">
                      <div><span className="text-gray-600">ID:</span> <span className="font-mono text-gray-900">{invoice.id}</span></div>
                      <div><span className="text-gray-600">Invoice #:</span> <span className="font-mono text-gray-900">{invoice.invoice_number || '-'}</span></div>
                      <div><span className="text-gray-600">Order #:</span> <span className="font-mono text-gray-900">{invoice.order_number || '-'}</span></div>
                      <div><span className="text-gray-600">Status:</span> <span className="font-mono text-gray-900 capitalize">{invoice.status || '-'}</span></div>
                      <div><span className="text-gray-600">Mode:</span> <span className="font-mono text-gray-900 capitalize">{invoice.mode || '-'}</span></div>
                    </div>
                  </div>
                  <div>
                    <h4 className="font-semibold text-gray-900 mb-3">Dates & Parties</h4>
                    <div className="space-y-2 text-sm">
                      <div><span className="text-gray-600">Created:</span> <span className="font-mono text-gray-900">{invoice.created_at || '-'}</span></div>
                      <div><span className="text-gray-600">Due:</span> <span className="font-mono text-gray-900">{invoice.due_date || '-'}</span></div>
                      <div><span className="text-gray-600">Seller:</span> <span className="font-mono text-gray-900">{invoice.seller_name || '-'}</span></div>
                      <div><span className="text-gray-600">Buyer:</span> <span className="font-mono text-gray-900">{invoice.buyer_name || '-'}</span></div>
                      <div><span className="text-gray-600">Buyer Email:</span> <span className="font-mono text-gray-900 break-all">{invoice.buyer_email || '-'}</span></div>
                    </div>
                  </div>
                  <div>
                    <h4 className="font-semibold text-gray-900 mb-3">Financial</h4>
                    <div className="space-y-2 text-sm">
                      <div><span className="text-gray-600">Subtotal:</span> <span className="font-mono text-gray-900">${(invoice.subtotal || 0).toFixed(2)}</span></div>
                      <div><span className="text-gray-600">VAT:</span> <span className="font-mono text-gray-900">${(invoice.vat_amount || 0).toFixed(2)}</span></div>
                      <div><span className="text-gray-600">Total:</span> <span className="font-mono font-bold text-green-600">${(invoice.total || 0).toFixed(2)}</span></div>
                    </div>
                  </div>
                  <div>
                    <h4 className="font-semibold text-gray-900 mb-3">Payment & Links</h4>
                    <div className="space-y-2 text-sm">
                      <div><span className="text-gray-600">Payment System:</span> <span className="font-mono text-gray-900 capitalize">{invoice.payment_system || '-'}</span></div>
                      <div><span className="text-gray-600">TX ID:</span> <span className="font-mono text-gray-900 break-all text-xs">{invoice.blockchain_tx_id || '-'}</span></div>
                      <div><span className="text-gray-600">PDF URL:</span> <span className="font-mono text-gray-900 break-all text-xs">{invoice.pdf_url || '-'}</span></div>
                    </div>
                  </div>
                </div>
              </div>

              {/* Action Buttons */}
              <div className="flex gap-4 justify-center flex-wrap">
                <Link href="/dashboard" className="inline-flex items-center px-8 py-3 rounded-lg bg-green-600 text-white hover:bg-green-700 font-bold transition shadow hover:shadow-lg">
                  🏠 Dashboard
                </Link>
                <button
                  onClick={handleEdit}
                  className="inline-flex items-center px-8 py-3 rounded-lg bg-blue-600 text-white hover:bg-blue-700 font-bold transition shadow hover:shadow-lg"
                >
                  ✏️ Edit Invoice
                </button>
                <button
                  onClick={downloadPDF}
                  disabled={downloading}
                  className="inline-flex items-center px-8 py-3 rounded-lg bg-red-600 text-white hover:bg-red-700 disabled:opacity-60 disabled:cursor-not-allowed font-bold transition shadow hover:shadow-lg"
                >
                  {downloading ? '⏳ Downloading PDF...' : '📄 Download as PDF'}
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
                  className="inline-flex items-center px-8 py-3 rounded-lg bg-green-600 text-white hover:bg-green-700 font-bold transition shadow hover:shadow-lg"
                >
                  📊 Download as CSV
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </AuthGuard>
  );
}
