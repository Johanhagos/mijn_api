import Link from 'next/link';

// Coinbase Commerce redirects here after the customer submits a crypto payment.
// The payment is only final once the backend receives the confirmed webhook.
export default function PaymentSuccess() {
  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 px-4">
      <div className="max-w-md w-full bg-white rounded-lg shadow p-8 text-center">
        <h1 className="text-2xl font-bold text-gray-900 mb-3">Payment received</h1>
        <p className="text-gray-600 mb-6">
          Thank you. Your payment is being confirmed on the blockchain, which can take a few
          minutes.
        </p>
        <Link href="/login" className="inline-block bg-blue-600 text-white px-5 py-2 rounded hover:bg-blue-700">
          Go to dashboard
        </Link>
      </div>
    </div>
  );
}
