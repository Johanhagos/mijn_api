const { chromium } = require('playwright');
(async () => {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage();
  await page.goto('http://localhost:3001/login', { waitUntil: 'load' });
  const result = await page.evaluate(async () => {
    try {
      const res = await fetch('http://127.0.0.1:8001/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: 'merchant_test@example.com', password: 'merchant123' }),
        credentials: 'include'
      });
      const text = await res.text();
      return { status: res.status, ok: res.ok, text, headers: Array.from(res.headers.entries()) };
    } catch (e) {
      return { error: String(e) };
    }
  });
  console.log('fetch result:', result);
  await browser.close();
})();
