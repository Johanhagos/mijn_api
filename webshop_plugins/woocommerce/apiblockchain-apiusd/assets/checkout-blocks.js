// "Pay with APIUSD" in WooCommerce's block checkout. Placing the order redirects the
// customer to APIBlockchain's hosted checkout (handled by the PHP gateway).
(function () {
  var registry = window.wc && window.wc.wcBlocksRegistry;
  var wcSettings = window.wc && window.wc.wcSettings;
  if (!registry || !wcSettings) {
    return;
  }
  var el = window.wp.element.createElement;
  var decode = window.wp.htmlEntities.decodeEntities;
  var settings = wcSettings.getSetting('apiblockchain_apiusd_data', {});
  var title = decode(settings.title || 'Pay with APIUSD');

  var Content = function () {
    return el('div', null, decode(settings.description || ''));
  };

  registry.registerPaymentMethod({
    name: 'apiblockchain_apiusd',
    label: el('span', null, title),
    ariaLabel: title,
    content: el(Content),
    edit: el(Content),
    canMakePayment: function () { return true; },
    supports: { features: settings.supports || ['products'] }
  });
})();
