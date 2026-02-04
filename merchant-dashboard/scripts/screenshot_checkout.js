const { chromium } = require('playwright');
(async () => {
  const apiUrl = 'http://127.0.0.1:8002';
  const apiKey = 'sk_test_local_automation';

  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext();

  // Create a server-side session
  const resp = await context.request.post(`${apiUrl}/create_session`, {
    headers: { 'X-API-Key': apiKey, 'Content-Type': 'application/json' },
    data: { amount: 10, mode: 'test', success_url: '', cancel_url: '' }
  });

  if (!resp.ok()) {
    console.error('Failed to create session', resp.status(), await resp.text());
    await browser.close();
    process.exit(1);
  }

  const body = await resp.json();
  const sessionId = body.id || (body.session && body.session.id);
  if (!sessionId) {
    console.error('No session id returned', body);
    await browser.close();
    process.exit(1);
  }

  const checkoutUrl = `${apiUrl}/checkout?session=${sessionId}`;

  const page = await context.newPage();
  await page.goto(checkoutUrl, { waitUntil: 'networkidle' });
  // Give scripts a moment to render
  await page.waitForTimeout(500);

  const outPath = 'c:/Users/gebruiker/Desktop/mijn_api/merchant-dashboard/screenshots/checkout.png';
  await page.screenshot({ path: outPath, fullPage: true });
  console.log('screenshot saved to', outPath);

  await browser.close();
})();
