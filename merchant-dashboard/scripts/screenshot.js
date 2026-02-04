const { chromium } = require('playwright');
(async () => {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage();
  await page.goto('http://localhost:3001/login', { waitUntil: 'networkidle' });
  await page.fill('input[type="email"]', 'merchant_test@example.com');
  await page.fill('input[type="password"]', 'merchant123');
  await page.click('button:has-text("Login")');
  try {
    await page.waitForURL('**/dashboard', { timeout: 10000 });
  } catch (e) {
    // allow some extra time for navigation
    await page.waitForTimeout(2000);
  }
  await page.screenshot({ path: 'c:/Users/gebruiker/Desktop/mijn_api/merchant-dashboard/screenshots/dashboard.png', fullPage: true });
  await browser.close();
  console.log('screenshot saved');
})();
