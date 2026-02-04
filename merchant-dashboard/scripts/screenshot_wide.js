const { chromium } = require('playwright');
(async () => {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 1280, height: 800 } });
  await page.goto('http://localhost:3001/login', { waitUntil: 'networkidle' });
  await page.fill('input[type="email"]', 'merchant_test@example.com');
  await page.fill('input[type="password"]', 'merchant123');
  await page.click('button:has-text("Login")');
  try {
    await page.waitForURL('**/dashboard', { timeout: 20000 });
  } catch (e) {
    await page.waitForTimeout(2000);
  }
  await page.screenshot({ path: 'c:/Users/gebruiker/Desktop/mijn_api/merchant-dashboard/screenshots/dashboard_1280x800.png', fullPage: false });
  await browser.close();
  console.log('screenshot saved');
})();
