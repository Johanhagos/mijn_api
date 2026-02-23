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
    const msg = userMessage.toLowerCase().trim();

    // === WELCOMING FIRST-TIME MESSAGE ===
    if (msg === 'hi' || msg === 'hello' || msg === 'help' || msg === 'start' || msg === 'begin' || 
        msg.includes('hey') || msg.includes('how are you') || msg.includes('how do you do') || 
        msg.includes('what\'s up') || msg.includes('how\'s it going')) {
      return `👋 Welcome to APIBlockchain AI Assistant!

**I'm here to help you with:**

📊 **Dashboard & Metrics**
• Understand your revenue trends
• Analyze transaction data
• Track Web2 vs Web3 sales
• Monitor payment performance

💰 **Payment Setup**
• Configure payment methods
• Enable Web3 (crypto) payments
• Understand settlement times
• Troubleshoot payment issues

📋 **Tax & Compliance** 
• Explain VAT/tax rates (60+ countries)
• Help with invoice requirements
• Guide on tax filing deadlines
• EU B2B reverse charge rules

🧾 **Invoicing & Customers**
• Generate compliant invoices
• Answer customer questions
• Explain tax charges
• Handle refund requests

🪙 **Crypto & Web3**
• Bitcoin, Ethereum, USDC payments
• Multi-blockchain support
• Settlement tracking
• Rate & fee explanations

🌍 **International Business**
• Multi-country tax support
• Currency conversion info
• Cross-border payment rules
• Compliance by region

**Quick Examples:**
• "How do I enable crypto payments?"
• "What tax applies to my sales?"
• "How do I explain charges to customers?"
• "Why is my revenue low?"
• "Help with EU VAT"

**What would you like help with?**`;
    }

    // === CUSTOMER SUPPORT (help merchants answer customer questions) ===
    if (msg.includes('customer ask') || msg.includes('customer wants') || msg.includes('customer question') || msg.includes('how do i tell customer') || msg.includes('customer received invoice')) {
      return `🙋‍♂️ HELPING YOUR CUSTOMERS:

Common Customer Questions:

💳 **Payment Issues:**
"We accept cards, bank transfers, and crypto (Bitcoin/Ethereum/USDC). All payments are secure with confirmation emails."

🪙 **Crypto Payment:**
"Select 'Pay with Crypto' → Choose currency → Scan QR code with your wallet → Send exact amount → Wait 10-30 min for confirmation."

💰 **Why Tax/VAT Charged:**
"Tax is legally required based on your country. The rate depends on buyer/seller countries. We collect and report it to tax authorities for compliance."

🔄 **Refunds:**
"Contact me (merchant) first - I can process refunds faster. For card/PayPal, you can dispute if needed. Crypto refunds must come from me (irreversible!)."

📄 **Lost Invoice:**
"You should have received it via email. Check spam folder. I can resend from my dashboard if needed."

Want specific wording for a customer question? Ask me!`;
    }

    // Customer crypto payment help
    if (msg.includes('customer crypto') || msg.includes('customer bitcoin') || msg.includes('explain crypto to customer') || msg.includes('customer doesn\'t know crypto')) {
      return `🪙 EXPLAINING CRYPTO TO CUSTOMERS:

Simple Message Template:

"Hi! Crypto payments are easy:

1. Click 'Pay with Crypto' at checkout
2. Choose Bitcoin, Ethereum, or USDC
3. You'll see a QR code and wallet address
4. Open your crypto wallet app (like Coinbase or MetaMask)
5. Scan the QR code OR paste the address
6. Send the EXACT amount shown
7. Payment confirms in 10-30 minutes

⚠️ Important:
• Send exact amount (not more/less)
• Use correct network (Bitcoin → BTC, Ethereum → ETH)
• Don't close the page until you see confirmation
• Small network fees will apply (separate from your order)

No crypto wallet? No worries - you can pay with card or bank transfer instead!"

Copy this message and customize for your customer! 📋`;
    }

    // Customer tax/VAT questions
    if (msg.includes('customer tax') || msg.includes('customer vat') || msg.includes('why charged tax') || msg.includes('explain tax to customer')) {
      return `💰 EXPLAINING TAX/VAT TO CUSTOMERS:

Simple Message Template:

"The tax/VAT on your invoice is required by law and depends on:
• Your country
• My country (seller)
• Type of transaction (B2B or B2C)

Where the tax goes:
I collect it and pay it to tax authorities. It's tracked for compliance and audits.

Common situations:
🇪🇺 EU Customers (B2C): VAT based on your country rate
🏢 EU Business (B2B): If you provide VAT ID, reverse charge applies (0% VAT - you pay tax in your country)
🌍 Outside EU: Usually 0% VAT, but local taxes may apply in your country

Your invoice shows the full breakdown: base price + tax rate + tax amount.

If you're a registered business with VAT ID, send it to me for reverse charge!"

This explains it clearly for customers! 📊`;
    }

    // Customer refund handling
    if (msg.includes('customer refund') || msg.includes('how to refund customer') || msg.includes('customer wants money back') || msg.includes('issue refund')) {
      return `🔄 HANDLING CUSTOMER REFUNDS:

**Your Process:**
1. Confirm the refund request (check order details)
2. Process refund through your dashboard or payment processor
3. Notify customer with confirmation

**By Payment Method:**
💳 **Card Payments:** Refund through your payment processor (appears in 3-7 days)
🔵 **PayPal:** Use PayPal dashboard to refund (instant to their account)
🪙 **Crypto:** You must send crypto back to customer's wallet address (irreversible!)

**Template Message:**
"Your refund of [amount] has been processed. For card payments, it takes 3-7 business days to appear. For PayPal, it's instant. You'll see a confirmation email."

**⚠️ Crypto Refunds:**
Ask customer for wallet address → Verify it's correct → Send exact amount → Get confirmation

Want help with specific refund scenario? Ask me!`;
    }

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
    
    // INTERNATIONAL TAX & COMPLIANCE SYSTEM (60+ COUNTRIES)
    if (msg.includes('international tax') || msg.includes('global tax') || msg.includes('tax compliance') || msg.includes('worldwide tax')) {
      return "Our system supports 60+ countries across 5 regions (EU, Americas, Asia-Pacific, Middle East/Africa, Europe). Automatic tax calculation based on seller/buyer countries. Works for any seller location with local compliance rules.";
    }
    if (msg.includes('vat') || msg.includes('tax') || msg.includes('compliance')) {
      return `VAT & TAX COMPLIANCE WORLDWIDE:
🇪🇺 EU (27 countries): 17-27% VAT. B2B reverse charge supported. EU B2C cross-border handled automatically.
🇬🇧 UK: 20% VAT, Switzerland: 7.7%, Norway: 25%, Iceland: 24%
🇺🇸 Americas: USA (0% federal), Canada (5% GST + provincial), Mexico 16%, Brazil 15%, Argentina 21%
🇯🇵 Asia-Pacific: Japan 10%, Australia 10% GST, China 13%, India 18%, Singapore 8%
🇦🇪 Middle East & Africa: UAE 5%, Saudi Arabia 15%, South Africa 15%, Nigeria 7.5%
✅ Same country sales use seller's local rate
✅ Cross-border exports automatically 0% when applicable
✅ B2B reverse charges calculated for EU`;
    }
    
    // REGIONAL TAX DETAILS
    if (msg.includes('eu vat') || msg.includes('european vat') || msg.includes('vat rate')) {
      return `EU VAT RATES (27 countries, automatic application):
Austria 20% | Belgium 21% | Bulgaria 20% | Croatia 25% | Cyprus 19% | Czech Rep 21% | Denmark 25% | Estonia 20% | Finland 24% | France 20% | Germany 19% | Greece 24% | Hungary 27% | Ireland 23% | Italy 22% | Latvia 21% | Lithuania 21% | Luxembourg 17% | Malta 18% | Netherlands 21% | Poland 23% | Portugal 23% | Romania 19% | Slovakia 20% | Slovenia 22% | Spain 21% | Sweden 25%

Key Rules:
• Same country (seller=buyer): Apply seller's VAT rate
• EU B2C cross-border: Apply seller's VAT rate
• EU B2B (with valid VAT ID): 0% + Reverse charge note
• EU to non-EU exports: 0% VAT (with export proof)
✅ We handle all combinations automatically`;
    }
    
    // US & AMERICAS TAX
    if (msg.includes('us tax') || msg.includes('sales tax') || msg.includes('usa tax') || msg.includes('americas tax')) {
      return `AMERICAS TAX SYSTEM:
🇺🇸 USA: 0% federal (varies by state). We track seller state for compliance.
🇨🇦 Canada: 5% federal GST + Provincial PST (varies by province 0-15%)
🇲🇽 Mexico: 16% IVA standard rate
🇧🇷 Brazil: 15% ICMS (varies by state and product)
🇦🇷 Argentina: 21% IVA, reduced rates (5-10.5%) for essentials
🇨🇱 Chile: 19% IVA
🇨🇴 Colombia: 19% IVA, 5% reduced rate for basic goods

For multi-state US sales, merchant can provide state code for compliance tracking.`;
    }
    
    // ASIA-PACIFIC TAX
    if (msg.includes('asia tax') || msg.includes('asia pacific') || msg.includes('japan tax') || msg.includes('australia tax') || msg.includes('china tax')) {
      return `ASIA-PACIFIC TAX SYSTEM:
🇯🇵 Japan: 10% standard, 8% reduced (food)
🇦🇺 Australia: 10% GST (same rate nationwide)
🇳🇿 New Zealand: 15% GST
🇰🇷 South Korea: 10% standard VAT
🇨🇳 China: 13% standard, 9% (transport), 6% (services)
🇮🇳 India: 18% standard GST, 12% (certain goods), 5% (essentials)
🇸🇬 Singapore: 8% GST
🇹🇭 Thailand: 7% VAT
🇮🇩 Indonesia: 11% PPN (Value Added Tax)
🇲🇾 Malaysia: 6% SST (Sales & Service Tax)

All rates applied automatically based on seller/buyer location.`;
    }
    
    // MIDDLE EAST & AFRICA TAX
    if (msg.includes('middle east tax') || msg.includes('africa tax') || msg.includes('uae tax') || msg.includes('saudi tax')) {
      return `MIDDLE EAST & AFRICA TAX SYSTEM:
🇦🇪 UAE: 5% VAT (implemented 2018)
🇸🇦 Saudi Arabia: 15% VAT
🇪🇬 Egypt: 14% standard VAT
🇿🇦 South Africa: 15% VAT
🇳🇬 Nigeria: 7.5% VAT
🇰🇪 Kenya: 16% VAT
🇴🇲 Oman: 5% VAT
🇶🇦 Qatar: No VAT currently (exemptions apply)

These regions are rapidly implementing digital tax systems, and we're ready for compliance tracking.`;
    }
    
    // REVERSE CHARGE & B2B
    if (msg.includes('reverse charge') || msg.includes('b2b') || msg.includes('vat id') || msg.includes('business to business')) {
      return `REVERSE CHARGE & B2B COMPLIANCE:
When seller & buyer are both in EU with valid business VAT numbers:
• Invoice shows 0% VAT
• Note: "VAT Reverse Charge - Customer liable" 
• Buyer country VAT ID validated & stored
• Seller reports as zero-rated export
• Buyer reports as import + self-billing

We automatically:
✅ Detect B2B transactions (VAT ID format validation)
✅ Apply 0% rate instead of standard VAT
✅ Add reverse charge note to invoice
✅ Flag for audit trail (7-year retention)`;
    }
    
    // EXPORT & ZERO RATE
    if (msg.includes('export') || msg.includes('zero rate') || msg.includes('zero rated')) {
      return `ZERO-RATED EXPORTS (0% TAX):
When EU seller ships to non-EU country:
• 0% VAT applied (export rule)
• Proof of export required (shipping address, VAT ID if B2B)
• Invoice marked: "Services/goods export - VAT exempt"

Non-EU sellers selling to non-residents typically charge their local tax rate.

We handle the export rules automatically when buyer country ≠ seller country.`;
    }
    
    // INVOICE COMPLIANCE
    if (msg.includes('invoice') || msg.includes('invoicing') || msg.includes('audit trail') || msg.includes('record keeping')) {
      return `COMPLIANT INVOICING (ALL COUNTRIES):
Every invoice automatically includes:
✅ Seller country & tax ID
✅ Buyer country & location
✅ Applicable tax rate & calculation
✅ Tax amount breakdown
✅ Reverse charge flag (if applicable)
✅ Timestamp & blockchain proof-of-payment
✅ Transaction ID (payment/crypto)

All invoices stored 7+ years for audit. GDPR-compliant. Accessible via dashboard & API.`;
    }
    
    // TAX REPORTING
    if (msg.includes('tax reporting') || msg.includes('tax report') || msg.includes('tax filing') || msg.includes('belastingaangifte')) {
      return `AUTOMATIC TAX REPORTING:
Export your transactions by:
• Country pairs (seller→buyer)
• Tax rate applied
• Invoice date range
• Sum totals for tax authorities

Perfect for:
🇳🇱 Netherlands: IB & aangifte VAT
🇩🇪 Germany: Umsatzsteuer-Voranmeldung
🇫🇷 France: TVA monthly/quarterly
🇪🇸 Spain: Modelo 390 (annual)
🇮🇹 Italy: Esterometro (foreign sales)
🇧🇪 Belgium: INTRASTAT & VAT reporting
+ 54 other countries

The system handles international combinations so you stay compliant everywhere.`;
    }
    
    if (msg.includes('compliance') || msg.includes('tax')) {
      return "We handle automatic VAT/tax calculation per international regulations, generate legally-compliant invoices, maintain 7-year audit trails, and support OSS (One-Stop Shop) for cross-border EU sales. Fully auditable blockchain records. Works for 60+ countries.";
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
          <div className="flex-1 overflow-y-auto p-4 space-y-4 bg-gradient-to-b from-emerald-50 via-white to-emerald-50">
            {messages.map((msg, idx) => (
              <div
                key={idx}
                className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'} animate-in fade-in slide-in-from-bottom-2`}
              >
                <div
                  className={`max-w-[75%] rounded-2xl px-4 py-3 ${
                    msg.role === 'user'
                      ? 'bg-gradient-to-br from-emerald-600 to-cyan-600 text-white shadow-lg'
                      : 'bg-emerald-100 text-slate-900 border border-emerald-400/50 shadow-md'
                  }`}
                >
                  <p className="text-sm whitespace-pre-wrap leading-relaxed">{msg.content}</p>
                  <p className={`text-xs mt-2 ${msg.role === 'user' ? 'text-white/70' : 'text-emerald-700'}`}>
                    {msg.timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                  </p>
                </div>
              </div>
            ))}
            {isLoading && (
              <div className="flex justify-start">
                <div className="bg-emerald-50 border border-emerald-300/50 rounded-2xl px-4 py-3 shadow-md">
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
            <div className="px-4 py-2 border-t border-emerald-200">
              <p className="text-xs text-emerald-700 mb-2">Quick actions:</p>
              <div className="flex flex-wrap gap-2">
                {quickActions.map((action, idx) => (
                  <button
                    key={idx}
                    onClick={() => setInput(action)}
                    className="text-xs px-3 py-1 bg-emerald-500 hover:bg-emerald-600 text-white rounded-full border border-emerald-400/50 transition"
                  >
                    {action}
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* Input */}
          <div className="p-4 border-t border-emerald-300/50 bg-emerald-50 space-y-3">
            <div className="flex gap-2">
              <input
                type="text"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyPress={handleKeyPress}
                placeholder="Ask me anything about your dashboard..."
                className="flex-1 px-4 py-2.5 bg-white border border-emerald-400/60 rounded-xl text-slate-900 placeholder-slate-400 focus:outline-none focus:border-emerald-500 focus:ring-2 focus:ring-emerald-400/30 transition-all duration-200"
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
