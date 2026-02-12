import React, { useState } from 'react';
import api from '../lib/api';

interface VATCheckResult {
  valid: boolean | null;
  vat_number: string;
  country: string;
  company_name?: string;
  address?: string;
  message: string;
}

export default function VATChecker() {
  const [vatNumber, setVatNumber] = useState('');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<VATCheckResult | null>(null);
  const [error, setError] = useState('');

  const handleCheck = async () => {
    if (!vatNumber.trim()) {
      setError('Please enter a VAT number');
      return;
    }

    setLoading(true);
    setError('');
    setResult(null);

    try {
      const response = await api.protectedApi('/validate-vat', 'POST', {
        vat_number: vatNumber,
      });

      setResult(response);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to validate VAT number');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter') {
      handleCheck();
    }
  };

  return (
    <div className="card p-6 mb-6">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-xl font-bold">🇪🇺 VAT Number Checker</h2>
        <span className="text-xs bg-green-100 text-green-800 px-2 py-1 rounded">EU VIES</span>
      </div>

      <p className="text-gray-600 text-sm mb-4">
        Validate if a VAT number is compliant and registered in the EU VIES system.
      </p>

      <div className="flex gap-2 mb-4">
        <input
          type="text"
          value={vatNumber}
          onChange={(e) => setVatNumber(e.target.value.toUpperCase())}
          onKeyPress={handleKeyPress}
          placeholder="Enter VAT number (e.g., DE123456789, FR12345678901)"
          className="flex-1 px-3 py-2 border border-gray-300 rounded focus:outline-none focus:ring-2 focus:ring-green-500"
          disabled={loading}
        />
        <button
          onClick={handleCheck}
          disabled={loading || !vatNumber.trim()}
          className={`px-4 py-2 rounded font-medium text-white transition-colors ${
            loading || !vatNumber.trim()
              ? 'bg-gray-400 cursor-not-allowed'
              : 'bg-green-600 hover:bg-green-700 active:bg-green-800'
          }`}
        >
          {loading ? 'Checking...' : 'Check VAT'}
        </button>
      </div>

      {error && (
        <div className="p-3 mb-4 bg-red-100 text-red-800 rounded border border-red-300">
          {error}
        </div>
      )}

      {result && (
        <div
          className={`p-4 rounded border-l-4 ${
            result.valid === true
              ? 'bg-green-50 border-green-400 text-green-900'
              : result.valid === false
              ? 'bg-red-50 border-red-400 text-red-900'
              : 'bg-yellow-50 border-yellow-400 text-yellow-900'
          }`}
        >
          <div className="font-bold text-lg mb-2">
            {result.valid === true
              ? '✓ Valid VAT Number'
              : result.valid === false
              ? '✗ Invalid VAT Number'
              : '⚠ Service Unavailable'}
          </div>

          <div className="text-sm space-y-2">
            <p>
              <span className="font-semibold">VAT Number:</span> {result.vat_number}
            </p>
            <p>
              <span className="font-semibold">Country:</span> {result.country}
            </p>

            {result.company_name && (
              <p>
                <span className="font-semibold">Company Name:</span> {result.company_name}
              </p>
            )}

            {result.address && (
              <p>
                <span className="font-semibold">Address:</span> {result.address}
              </p>
            )}

            <p className="mt-3 pt-2 border-t border-current/20 italic">
              {result.message}
            </p>
          </div>
        </div>
      )}

      <div className="mt-4 pt-4 border-t border-gray-200 text-xs text-gray-600">
        <p className="mb-2">
          <strong>Supported Countries:</strong> All EU member states (AT, BE, BG, CY, CZ, DE, DK, EE, ES, FI, FR, GR, HR, HU, IE, IT, LT, LU, LV, MT, NL, PL, PT, RO, SE, SI, SK) plus GB and XI (for UK).
        </p>
        <p>
          <strong>VAT Format:</strong> 2-letter country code followed by the VAT number (e.g., DE123456789 for a German company).
        </p>
      </div>
    </div>
  );
}
