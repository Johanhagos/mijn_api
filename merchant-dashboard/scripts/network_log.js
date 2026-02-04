const { chromium } = require('playwright');
(async () => {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage();
  page.on('request', req => {
    if (req.url().includes('/login')) console.log('REQ:', req.method(), req.url(), req.headers());
  });
  page.on('response', async res => {
    if (res.url().includes('/login')) {
      console.log('RES:', res.status(), res.url());
      try { console.log('RES HEADERS:', res.headers()); } catch (e) { console.log('HEADERS ERR', e); }
      try { const t = await res.text(); console.log('RES BODY:', t); } catch (e) { console.log('BODY ERR', e); }
    }
  });

  await page.goto('http://localhost:3001/login', { waitUntil: 'load' });
  await page.fill('input[type="email"]', 'merchant_test@example.com');
  await page.fill('input[type="password"]', 'merchant123');
  await page.click('button:has-text("Login")');
  // wait a bit for responses
  await page.waitForTimeout(3000);
  await browser.close();
})();
