import { useEffect, useState } from 'react';
import { useRouter } from 'next/router';
import Link from 'next/link';
import api from '../../lib/api';
import AuthGuard from '../../components/AuthGuard';
import Header from '../../components/Header';

export default function CreateInvoice() {
  const router = useRouter();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [logoUrl, setLogoUrl] = useState('');
  
  const [formData, setFormData] = useState({
    // Seller info
    seller_name: '',
    seller_vat: '',
    seller_address: '',
    seller_country: '',
    
    // Buyer info
    buyer_name: '',
    buyer_vat: '',
    buyer_address: '',
    buyer_country: '',
    buyer_type: 'B2C', // B2B or B2C
    
    // Invoice details
    invoice_number: '', // Auto-generated if empty
    order_number: '',
    due_date: '',
    
    // Items
    description: '',
    quantity: 1,
    unit_price: 0,
    
    // VAT
    vat_rate: 21, // Default 21%, set to 0 for B2B
    
    // Payment
    payment_system: 'web2', // web2 or web3
    
    // Notes
    notes: '',
    
    // Status
    status: 'issued', // issued, draft, paid
  });

  // Load merchant logo on mount
  useEffect(() => {
    const loadLogo = async () => {
      try {
        const response = await api.protectedApi('/merchant/logo');
        if (response.logo_url) {
          setLogoUrl(response.logo_url);
        }
      } catch (err) {
        console.log('No logo uploaded yet');
      }
    };
    loadLogo();
  }, []);

  // Auto-set VAT rate based on buyer type
  useEffect(() => {
    if (formData.buyer_type === 'B2B' && formData.buyer_vat) {
      setFormData(prev => ({ ...prev, vat_rate: 0 }));
    } else if (formData.buyer_type === 'B2C') {
      setFormData(prev => ({ ...prev, vat_rate: 21 }));
    }
  }, [formData.buyer_type, formData.buyer_vat]);

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>) => {
    const { name, value } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: name === 'quantity' || name === 'unit_price' || name === 'vat_rate' ? parseFloat(value) : value
    }));
  };

  const handleLogoUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    try {
      const formDataUpload = new FormData();
      formDataUpload.append('file', file);
      
      const token = localStorage.getItem('jwt');
      const response = await fetch('https://api.apiblockchain.io/merchant/logo', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
        },
        body: formDataUpload,
      });

      if (response.ok) {
        const result = await response.json();
        setLogoUrl(result.logo_url);
        alert('Logo uploaded successfully!');
      } else {
        alert('Failed to upload logo');
      }
    } catch (err) {
      console.error('Logo upload error:', err);
      alert('Error uploading logo');
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError('');

    try {
      // Validate required fields
      if (!formData.seller_name || !formData.buyer_name || formData.quantity <= 0 || formData.unit_price <= 0) {
        setError('Please fill in all required fields');
        setLoading(false);
        return;
      }

      const payload = {
        ...formData,
        items: [{
          description: formData.description,
          quantity: formData.quantity,
          unit_price: formData.unit_price,
        }],
        merchant_logo_url: logoUrl || undefined,
        subtotal: parseFloat((formData.quantity * formData.unit_price).toFixed(2)),
      };

      const response = await api.protectedApi('/invoices', 'POST', payload);

      if (response && response.invoice_number) {
        router.push(`/invoices/${response.id}`);
      }
    } catch (err: any) {
      setError(err?.message || 'Failed to create invoice');
      console.error('Invoice creation error:', err);
    } finally {
      setLoading(false);
    }
  };

  const subtotal = parseFloat((formData.quantity * formData.unit_price).toFixed(2)) || 0;
  const vat = parseFloat((subtotal * (formData.vat_rate / 100)).toFixed(2)) || 0;
  const total = parseFloat((subtotal + vat).toFixed(2)) || 0;

  return (
    <AuthGuard>
      <div className="min-h-screen bg-gradient-to-br from-gray-50 to-gray-100">
        <Header />
        
        <div className="max-w-4xl mx-auto px-4 py-8">
          <div className="mb-6 flex items-center justify-between">
            <h1 className="text-4xl font-bold text-gray-900">Create Invoice</h1>
            <Link href="/invoices" className="inline-flex items-center px-4 py-2 rounded-lg bg-gray-600 text-white hover:bg-gray-700 font-medium transition">
              ← Back to Invoices
            </Link>
          </div>

          {error && (
            <div className="mb-6 p-4 rounded-lg bg-red-50 border border-red-200 text-red-700">
              {error}
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-8">
            {/* Logo Upload */}
            <div className="bg-white rounded-lg shadow p-6">
              <h2 className="text-2xl font-bold text-gray-900 mb-4">Logo</h2>
              <div className="flex items-center gap-4">
                {logoUrl && (
                  <img src={logoUrl} alt="Logo" className="h-20 w-20 object-cover rounded border border-gray-200" />
                )}
                <label className="cursor-pointer px-4 py-2 rounded-lg bg-green-600 text-white hover:bg-green-700 transition">
                  Upload Logo
                  <input
                    type="file"
                    accept="image/*"
                    onChange={handleLogoUpload}
                    className="hidden"
                  />
                </label>
              </div>
            </div>

            {/* Seller Section */}
            <div className="bg-white rounded-lg shadow p-6">
              <h2 className="text-2xl font-bold text-gray-900 mb-4">Seller Information</h2>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <input
                  type="text"
                  name="seller_name"
                  placeholder="Company Name *"
                  value={formData.seller_name}
                  onChange={handleChange}
                  className="w-full px-4 py-2 rounded border border-gray-300 focus:outline-none focus:ring-2 focus:ring-green-500"
                  required
                />
                <input
                  type="text"
                  name="seller_vat"
                  placeholder="VAT Number (e.g., DE123456789)"
                  value={formData.seller_vat}
                  onChange={handleChange}
                  className="w-full px-4 py-2 rounded border border-gray-300 focus:outline-none focus:ring-2 focus:ring-green-500"
                />
                <textarea
                  name="seller_address"
                  placeholder="Address"
                  value={formData.seller_address}
                  onChange={handleChange}
                  rows={2}
                  className="w-full px-4 py-2 rounded border border-gray-300 focus:outline-none focus:ring-2 focus:ring-green-500 md:col-span-2"
                />
                <input
                  type="text"
                  name="seller_country"
                  placeholder="Country (e.g., NL)"
                  value={formData.seller_country}
                  onChange={handleChange}
                  className="w-full px-4 py-2 rounded border border-gray-300 focus:outline-none focus:ring-2 focus:ring-green-500"
                />
              </div>
            </div>

            {/* Buyer Section */}
            <div className="bg-white rounded-lg shadow p-6">
              <h2 className="text-2xl font-bold text-gray-900 mb-4">Buyer Information</h2>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <input
                  type="text"
                  name="buyer_name"
                  placeholder="Company/Customer Name *"
                  value={formData.buyer_name}
                  onChange={handleChange}
                  className="w-full px-4 py-2 rounded border border-gray-300 focus:outline-none focus:ring-2 focus:ring-green-500"
                  required
                />
                <select
                  name="buyer_type"
                  value={formData.buyer_type}
                  onChange={handleChange}
                  className="w-full px-4 py-2 rounded border border-gray-300 focus:outline-none focus:ring-2 focus:ring-green-500"
                >
                  <option value="B2C">B2C (Consumer)</option>
                  <option value="B2B">B2B (Business)</option>
                </select>
                <input
                  type="text"
                  name="buyer_vat"
                  placeholder="VAT Number (B2B only)"
                  value={formData.buyer_vat}
                  onChange={handleChange}
                  className="w-full px-4 py-2 rounded border border-gray-300 focus:outline-none focus:ring-2 focus:ring-green-500"
                />
                <input
                  type="text"
                  name="buyer_country"
                  placeholder="Country (e.g., DE)"
                  value={formData.buyer_country}
                  onChange={handleChange}
                  className="w-full px-4 py-2 rounded border border-gray-300 focus:outline-none focus:ring-2 focus:ring-green-500"
                />
                <textarea
                  name="buyer_address"
                  placeholder="Address"
                  value={formData.buyer_address}
                  onChange={handleChange}
                  rows={2}
                  className="w-full px-4 py-2 rounded border border-gray-300 focus:outline-none focus:ring-2 focus:ring-green-500 md:col-span-2"
                />
              </div>
            </div>

            {/* Invoice Details */}
            <div className="bg-white rounded-lg shadow p-6">
              <h2 className="text-2xl font-bold text-gray-900 mb-4">Invoice Details</h2>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <input
                  type="text"
                  name="invoice_number"
                  placeholder="Invoice Number (auto-generated if empty)"
                  value={formData.invoice_number}
                  onChange={handleChange}
                  className="w-full px-4 py-2 rounded border border-gray-300 focus:outline-none focus:ring-2 focus:ring-green-500"
                />
                <input
                  type="text"
                  name="order_number"
                  placeholder="Order Number (optional)"
                  value={formData.order_number}
                  onChange={handleChange}
                  className="w-full px-4 py-2 rounded border border-gray-300 focus:outline-none focus:ring-2 focus:ring-green-500"
                />
                <input
                  type="date"
                  name="due_date"
                  value={formData.due_date}
                  onChange={handleChange}
                  className="w-full px-4 py-2 rounded border border-gray-300 focus:outline-none focus:ring-2 focus:ring-green-500"
                />
                <select
                  name="payment_system"
                  value={formData.payment_system}
                  onChange={handleChange}
                  className="w-full px-4 py-2 rounded border border-gray-300 focus:outline-none focus:ring-2 focus:ring-green-500"
                >
                  <option value="web2">💳 Web2 (Stripe/Card)</option>
                  <option value="web3">🔗 Web3 (Blockchain)</option>
                </select>
              </div>
            </div>

            {/* Line Item */}
            <div className="bg-white rounded-lg shadow p-6">
              <h2 className="text-2xl font-bold text-gray-900 mb-4">Line Item</h2>
              <div className="grid grid-cols-1 gap-4">
                <textarea
                  name="description"
                  placeholder="Description *"
                  value={formData.description}
                  onChange={handleChange}
                  rows={3}
                  className="w-full px-4 py-2 rounded border border-gray-300 focus:outline-none focus:ring-2 focus:ring-green-500"
                  required
                />
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">Quantity</label>
                    <input
                      type="number"
                      name="quantity"
                      value={formData.quantity}
                      onChange={handleChange}
                      min="0.01"
                      step="0.01"
                      className="w-full px-4 py-2 rounded border border-gray-300 focus:outline-none focus:ring-2 focus:ring-green-500"
                      required
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">Unit Price (EUR)</label>
                    <input
                      type="number"
                      name="unit_price"
                      value={formData.unit_price}
                      onChange={handleChange}
                      min="0"
                      step="0.01"
                      className="w-full px-4 py-2 rounded border border-gray-300 focus:outline-none focus:ring-2 focus:ring-green-500"
                      required
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">VAT Rate (%)</label>
                    <input
                      type="number"
                      name="vat_rate"
                      value={formData.vat_rate}
                      onChange={handleChange}
                      min="0"
                      max="100"
                      step="0.1"
                      className={`w-full px-4 py-2 rounded border focus:outline-none focus:ring-2 focus:ring-green-500 ${
                        formData.buyer_type === 'B2B' && formData.buyer_vat ? 'bg-gray-100 border-gray-300' : 'border-gray-300'
                      }`}
                      disabled={formData.buyer_type === 'B2B' && !!formData.buyer_vat}
                    />
                    {formData.buyer_type === 'B2B' && formData.buyer_vat && (
                      <p className="text-xs text-green-600 mt-1">B2B: VAT free (reverse charge)</p>
                    )}
                  </div>
                </div>
              </div>
            </div>

            {/* Totals Preview */}
            <div className="bg-gradient-to-r from-green-50 to-green-100 rounded-lg shadow p-6 border-l-4 border-green-600">
              <h3 className="text-lg font-bold text-gray-900 mb-4">Summary</h3>
              <div className="space-y-2">
                <div className="flex justify-between text-gray-700">
                  <span>Subtotal:</span>
                  <span className="font-semibold">EUR {subtotal.toFixed(2)}</span>
                </div>
                <div className="flex justify-between text-gray-700">
                  <span>VAT ({formData.vat_rate}%):</span>
                  <span className="font-semibold">EUR {vat.toFixed(2)}</span>
                </div>
                <div className="border-t-2 border-green-300 pt-2 flex justify-between text-xl font-bold text-green-700">
                  <span>Total:</span>
                  <span>EUR {total.toFixed(2)}</span>
                </div>
              </div>
            </div>

            {/* Notes */}
            <div className="bg-white rounded-lg shadow p-6">
              <h2 className="text-2xl font-bold text-gray-900 mb-4">Additional Information</h2>
              <textarea
                name="notes"
                placeholder="Notes or terms (optional)"
                value={formData.notes}
                onChange={handleChange}
                rows={4}
                className="w-full px-4 py-2 rounded border border-gray-300 focus:outline-none focus:ring-2 focus:ring-green-500"
              />
            </div>

            {/* Submit */}
            <div className="flex gap-4 justify-end">
              <Link href="/invoices" className="px-6 py-3 rounded-lg bg-gray-300 text-gray-900 hover:bg-gray-400 font-semibold transition">
                Cancel
              </Link>
              <button
                type="submit"
                disabled={loading}
                className="px-6 py-3 rounded-lg bg-green-600 text-white hover:bg-green-700 disabled:opacity-60 disabled:cursor-not-allowed font-semibold transition shadow hover:shadow-lg"
              >
                {loading ? '⏳ Creating Invoice...' : '✅ Create Invoice'}
              </button>
            </div>
          </form>
        </div>
      </div>
    </AuthGuard>
  );
}
