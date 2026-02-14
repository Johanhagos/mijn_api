import { useState, useRef, useEffect } from 'react';
import api from '../lib/api';

interface Message {
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
}

export default function AIAssistant({ merchantData, inline = false }: { merchantData?: any; inline?: boolean }) {
  const [isOpen, setIsOpen] = useState(false);
  const [messages, setMessages] = useState<Message[]>([
    {
      role: 'assistant',
      content: 'Hello! I\'m your AI assistant. I can help you understand your dashboard data, answer questions about transactions, provide insights, and guide you through features. How can I help you today?',
      timestamp: new Date()
    }
  ]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleSend = async () => {
    if (!input.trim() || isLoading) return;

    const userMessage: Message = {
      role: 'user',
      content: input,
      timestamp: new Date()
    };

    setMessages(prev => [...prev, userMessage]);
    setInput('');
    setIsLoading(true);

    try {
      const response = await api.protectedApi('/ai/chat', 'POST', {
        message: input,
        context: {
          ...merchantData,
          dashboard_context: 'merchant_portal',
          current_user_role: 'merchant_admin'
        },
        history: messages.slice(-10) // Last 10 messages for better context
      });

      const fallback = generateAIResponse(input);
      const assistantMessage: Message = {
        role: 'assistant',
        content: response?.reply || fallback,
        timestamp: new Date()
      };

      setMessages(prev => [...prev, assistantMessage]);
    } catch (error: any) {
      const fallback = generateAIResponse(input);
      const errorMessage: Message = {
        role: 'assistant',
        content: fallback,
        timestamp: new Date()
      };
      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const quickActions = [
    'Explain my revenue trend',
    'How do I integrate the plugin?',
    'What are Web3 transactions?',
    'Show me my top metrics',
    'How do I enable multi-currency?',
    'What is smart contract invoicing?',
    'Help with VAT compliance',
    'API integration guide'
  ];

  const generateAIResponse = (userMessage: string) => {
    const msg = userMessage.toLowerCase();

    // BLOCKCHAIN & PAYMENT PROCESSING CORE
    if (msg.includes('blockchain') || msg.includes('smart contract')) {
      return "Our smart contracts execute payment settlements automatically on multiple blockchains. They're immutable, transparent, and eliminate middlemen - reducing settlement time from 3 days to seconds!";
    }
    if (msg.includes('web3') || msg.includes('crypto payment') || msg.includes('cryptocurrency')) {
      return "Web3 payments let you accept 50+ cryptocurrencies (ETH, BTC, USDT, etc.). Funds settle in minutes, bypass traditional banking fees, and your customers can pay from anywhere in the world. Perfect for global merchants!";
    }
    if (msg.includes('settlement') || msg.includes('when do i get paid') || msg.includes('payout')) {
      return "With Web2 (credit cards): 1-3 business days. With Web3 (crypto): Settlement happens on-chain in minutes! Both methods show real-time status in your dashboard. Choose what works best for your business.";
    }

    // SECURITY & COMPLIANCE
    if (msg.includes('secure') || msg.includes('pci') || msg.includes('encryption') || msg.includes('fraud')) {
      return "We're PCI DSS Level 1 compliant, use military-grade SSL/TLS encryption, and blockchain transactions are cryptographically verified. All customer data is encrypted end-to-end. Fraud detection uses AI machine learning.";
    }
    if (msg.includes('compliance') || msg.includes('tax') || msg.includes('vat') || msg.includes('audit')) {
      return "We handle automatic VAT calculation per EU regulations, generate legally-compliant invoices, maintain 7-year audit trails, and support OSS (One-Stop Shop) for cross-border EU sales. Fully auditable blockchain records.";
    }
    if (msg.includes('pii') || msg.includes('privacy') || msg.includes('data protection') || msg.includes('gdpr')) {
      return "We process minimal customer data (email + payment info). All personally-identifiable information is encrypted separately. GDPR-compliant, right-to-be-forgotten supported, and data deletion within 30 days of request.";
    }

    // API & INTEGRATION
    if (msg.includes('api') || msg.includes('rest') || msg.includes('developer') || msg.includes('sdk')) {
      return "RESTful API with OAuth2 authentication. SDKs for Node.js, Python, PHP, Go, Ruby. Full webhook support for real-time events. Complete API docs at api.apiblockchain.io with sandbox for testing.";
    }
    if (msg.includes('integrate') || msg.includes('woocommerce') || msg.includes('shopify') || msg.includes('plugin')) {
      return "We offer plugins for WooCommerce, Shopify, and Magento. Or use our REST API for custom integrations. White-label options available. Average integration time: 2-4 hours with developer documentation.";
    }
    if (msg.includes('webhook') || msg.includes('notification') || msg.includes('event') || msg.includes('real-time')) {
      return "Real-time webhooks for all payment events: payment.started, payment.confirmed, payment.failed, invoice.created, refund.issued, etc. Retry logic with exponential backoff. Signed with HMAC-SHA256 for security.";
    }

    // INVOICING & SMART CONTRACTS
    if (msg.includes('invoice') || msg.includes('smart contract invoice')) {
      return "Smart contract invoicing means your invoices are cryptographically signed and stored on-chain - permanent, tamper-proof records. Perfect for B2B accounting and audits. Legally compliant in 30+ countries.";
    }
    if (msg.includes('recurring') || msg.includes('subscription') || msg.includes('billing')) {
      return "Support for recurring billing, subscriptions, and scheduled payments. Automatic retry logic for failed payments. Customer portal for managing subscriptions. Works with both Web2 and Web3 payments.";
    }

    // MULTI-CURRENCY & LOCALIZATION
    if (msg.includes('multi-currency') || msg.includes('currency conversion') || msg.includes('exchange rate')) {
      return "Accept payments in 150+ fiat currencies and 50+ cryptocurrencies. Real-time exchange rates via trusted providers. Automatic conversion or lock-in rates. Settlement in your preferred currency.";
    }
    if (msg.includes('localization') || msg.includes('language') || msg.includes('regional') || msg.includes('international')) {
      return "Dashboard and checkout available in 25+ languages. Regional payment methods (Alipay for China, Boleto for Brazil, etc). Local VAT/tax handling for all major markets.";
    }

    // MERCHANT DASHBOARD
    if (msg.includes('dashboard') || msg.includes('analytics') || msg.includes('reporting') || msg.includes('metrics')) {
      return "Real-time dashboard showing transactions, revenue, payment breakdown (Web2 vs Web3), geographic data, customer insights, and AI-powered trend analysis. Export reports for accounting and tax preparation.";
    }
    if (msg.includes('customer data') || msg.includes('customer info') || msg.includes('customer list')) {
      return "Secure customer database with transaction history, payment preferences, and retry logs. Built-in CRM features. Segmentation tools for targeted promotions. GDPR-compliant data management.";
    }

    // PRICING & PLANS
    if (msg.includes('starter') && (msg.includes('plan') || msg.includes('price') || msg.includes('features'))) {
      return "Starter (€20/month): Up to 100 transactions/month, basic API access, email support, essential analytics. Perfect for testing or small operations. Upgrade anytime.";
    }
    if (msg.includes('professional') && (msg.includes('plan') || msg.includes('price') || msg.includes('features'))) {
      return "Professional (€29.99/month): Unlimited transactions, full blockchain integration, merchant dashboard, multi-currency, smart contract invoicing, 24/7 priority support, advanced analytics. Our most popular plan!";
    }
    if (msg.includes('enterprise')) {
      return "Enterprise: Custom pricing for large-scale operations. Dedicated account manager, white-label options, custom API endpoints, SLA guarantees, priority feature requests. Contact sales@apiblockchain.io";
    }

    // PAYMENT METHODS
    if (msg.includes('paypal') || msg.includes('stripe') || msg.includes('payment method')) {
      return "We support Credit/Debit cards (Visa, Mastercard, Amex), Bank transfers (SEPA), PayPal, Apple Pay, Google Pay, and 50+ cryptocurrencies. Add or remove methods anytime from dashboard.";
    }
    if (msg.includes('crypto method') || msg.includes('which cryptocurrency') || msg.includes('bitcoin') || msg.includes('ethereum')) {
      return "Popular crypto payments: Bitcoin (BTC) - store of value, Ethereum (ETH) - smart contract ecosystem, USDT - price stable, USDC - regulatory compliant. We recommend stablecoins for e-commerce to avoid volatility.";
    }

    // SUPPORT & ONBOARDING
    if (msg.includes('support') || msg.includes('help') || msg.includes('contact')) {
      return "24/7 priority support for Pro+ customers. Email: support@apiblockchain.io | Phone: +31 (0)6 5282 4245. Live chat in dashboard. Response time: <30 minutes for urgent issues.";
    }
    if (msg.includes('onboarding') || msg.includes('training') || msg.includes('getting started')) {
      return "Free onboarding session: API setup, payment configuration, testing, and first live transaction. Video tutorials, docs, and code examples. 30-day money-back guarantee if you're not satisfied.";
    }
    if (msg.includes('demo') || msg.includes('sandbox') || msg.includes('test')) {
      return "Sandbox environment for risk-free testing. Use test API keys to simulate transactions without charges. Test payment webhooks, error handling, and integration flow before going live.";
    }

    // ADVANCED FEATURES
    if (msg.includes('refund') || msg.includes('dispute') || msg.includes('chargeback')) {
      return "Instant refunds with one-click processing. Dispute resolution with blockchain proof-of-payment. Chargeback protection through transparent transaction records.";
    }
    if (msg.includes('loyalty') || msg.includes('rewards') || msg.includes('cashback')) {
      return "Build loyalty programs with our rewards API. Award points for payments, redemption handling, and integration with your CRM. Available in Pro plan and above.";
    }
    if (msg.includes('fraud detection') || msg.includes('risk') || msg.includes('verification')) {
      return "AI-powered fraud detection with real-time risk scoring. 3D Secure for card payments. Multi-factor authentication options. Biometric verification available for crypto.";
    }

    // DEFAULT HELPFUL RESPONSES
    const contexts = [
      "Great! Ask me about payments, API integration, blockchain features, pricing, security, or customer support. What interests you?",
      "I can help with Web2/Web3 payments, smart contracts, VAT compliance, API integration, merchant features, or your favorite crypto. What would you like to know?",
      "Curious about blockchain technology, payment processing, international sales, or how our dashboard works? I'm here to help!",
      "Need info on pricing plans, payment methods, technical integration, security features, or VAT handling? Ask away!",
      "I'm knowledgeable about crypto payments, invoice management, analytics, compliance, and merchant tools. What's your question?"
    ];
    return contexts[Math.floor(Math.random() * contexts.length)];
  };

  return (
    <div
      style={
        inline
          ? { position: 'static', display: 'inline-flex', alignItems: 'center', gap: '8px', zIndex: 9999 }
          : { position: 'fixed', bottom: '24px', right: '24px', zIndex: 9999 }
      }
    >
      {/* Floating AI Button */}
      {!isOpen && (
        <button
          onClick={() => setIsOpen(true)}
          style={{
            minWidth: inline ? '140px' : '64px',
            height: inline ? '36px' : '64px',
            padding: inline ? '0 14px' : '0',
            borderRadius: inline ? '18px' : '50%',
            background: 'linear-gradient(to bottom right, #10b981, #06b6d4)',
            color: 'white',
            border: 'none',
            cursor: 'pointer',
            boxShadow: '0 10px 20px rgba(0, 0, 0, 0.25)',
            display: 'inline-flex',
            alignItems: 'center',
            justifyContent: 'center',
            gap: inline ? '8px' : '0',
            position: 'relative',
            fontSize: inline ? '12px' : '0'
          }}
          aria-label="Open AI Assistant"
        >
          <svg style={{ width: '32px', height: '32px' }} fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z" />
          </svg>
          {inline && <span style={{ fontWeight: 600 }}>Open AI Assistant</span>}
          <div style={{
            position: 'absolute',
            top: '-4px',
            right: '-4px',
            width: '16px',
            height: '16px',
            background: '#4ade80',
            borderRadius: '50%'
          }}></div>
        </button>
      )}

      {/* Chat Window */}
      {isOpen && (
        <div className="fixed bottom-6 right-6 z-50 w-96 h-[650px] bg-gradient-to-b from-slate-900 to-slate-950 rounded-2xl shadow-2xl border border-emerald-500/30 flex flex-col overflow-hidden">
          {/* Header */}
          <div className="bg-gradient-to-r from-emerald-600 to-cyan-600 p-4 flex items-center justify-between shadow-lg">
            <div className="flex items-center gap-3">
              <div className="w-8 h-8 bg-white/20 rounded-full flex items-center justify-center">
                <svg className="w-5 h-5 text-white" fill="currentColor" viewBox="0 0 20 20">
                  <path d="M2 11a1 1 0 011-1h2a1 1 0 011 1v5a1 1 0 01-1 1H3a1 1 0 01-1-1v-5zM8 7a1 1 0 011-1h2a1 1 0 011 1v9a1 1 0 01-1 1H9a1 1 0 01-1-1V7zM14 4a1 1 0 011-1h2a1 1 0 011 1v12a1 1 0 01-1 1h-2a1 1 0 01-1-1V4z" />
                </svg>
              </div>
              <div>
                <h3 className="text-white font-semibold text-sm">AI Assistant</h3>
                <p className="text-white/70 text-xs">Always here to help</p>
              </div>
            </div>
            <button
              onClick={() => setIsOpen(false)}
              className="text-white hover:bg-white/20 p-2 rounded-lg transition"
              aria-label="Close"
            >
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>

          {/* Messages */}
          <div className="flex-1 overflow-y-auto p-4 space-y-4 bg-gradient-to-b from-slate-900 via-slate-900 to-slate-950">
            {messages.map((msg, idx) => (
              <div
                key={idx}
                className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'} animate-in fade-in slide-in-from-bottom-2`}
              >
                <div
                  className={`max-w-[75%] rounded-2xl px-4 py-3 ${
                    msg.role === 'user'
                      ? 'bg-gradient-to-br from-emerald-600 to-cyan-600 text-white shadow-lg'
                      : 'bg-slate-700 text-white border border-emerald-400/50 shadow-md'
                  }`}
                >
                  <p className="text-sm whitespace-pre-wrap leading-relaxed">{msg.content}</p>
                  <p className={`text-xs mt-2 ${msg.role === 'user' ? 'text-white/70' : 'text-slate-300'}`}>
                    {msg.timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                  </p>
                </div>
              </div>
            ))}
            {isLoading && (
              <div className="flex justify-start">
                <div className="bg-slate-800 border border-emerald-500/30 rounded-2xl px-4 py-3 shadow-md">
                  <div className="flex gap-2">
                    <div className="w-2 h-2 bg-emerald-400 rounded-full animate-bounce"></div>
                    <div className="w-2 h-2 bg-emerald-400 rounded-full animate-bounce" style={{ animationDelay: '0.1s' }}></div>
                    <div className="w-2 h-2 bg-emerald-400 rounded-full animate-bounce" style={{ animationDelay: '0.2s' }}></div>
                  </div>
                </div>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>

          {/* Quick Actions */}
          {messages.length === 1 && (
            <div className="px-4 py-2 border-t border-slate-700">
              <p className="text-xs text-emerald-300 mb-2">Quick actions:</p>
              <div className="flex flex-wrap gap-2">
                {quickActions.map((action, idx) => (
                  <button
                    key={idx}
                    onClick={() => setInput(action)}
                    className="text-xs px-3 py-1 bg-slate-700 hover:bg-slate-600 text-emerald-100 rounded-full border border-emerald-400/50 transition"
                  >
                    {action}
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* Input */}
          <div className="p-4 border-t border-emerald-500/30 bg-slate-900 space-y-3">
            <div className="flex gap-2">
              <input
                type="text"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyPress={handleKeyPress}
                placeholder="Ask me anything about your dashboard..."
                className="flex-1 px-4 py-2.5 bg-slate-800 border border-emerald-500/60 rounded-xl text-white placeholder-slate-300 focus:outline-none focus:border-emerald-400 focus:ring-2 focus:ring-emerald-400/30 transition-all duration-200"
                disabled={isLoading}
              />
              <button
                onClick={handleSend}
                disabled={!input.trim() || isLoading}
                className="px-4 py-2.5 bg-gradient-to-r from-emerald-600 to-cyan-600 hover:from-emerald-500 hover:to-cyan-500 disabled:from-slate-600 disabled:to-slate-700 text-white rounded-xl font-medium transition-all duration-200 disabled:cursor-not-allowed shadow-lg hover:shadow-emerald-500/50"
              >
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
                </svg>
              </button>
            </div>
            <p className="text-xs text-slate-400 text-center">Available 24/7 • Powered by AI • Always learning</p>
          </div>
        </div>
      )}
    </div>
  );
}
