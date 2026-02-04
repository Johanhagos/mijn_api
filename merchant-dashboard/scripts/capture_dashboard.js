const { chromium } = require('playwright');
(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage();

  // Use the token obtained from the backend login
  const token = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJtZXJjaGFudF90ZXN0QGV4YW1wbGUuY29tIiwicm9sZSI6Im1lcmNoYW50IiwiZXhwIjoxNzY5OTU1OTMwfQ.M2NNHAPLoDJIMtU6fwZ4OdXx_GTgHHQTEqQV7dOU7g0';

  // Open the login page then set localStorage
  await page.goto('http://localhost:3001/login');
  await page.evaluate((t) => {
    localStorage.setItem('jwt', t);
    localStorage.setItem('merchant_id', '99');
    localStorage.setItem('merchant_email', 'merchant_test@example.com');
  }, token);

  // Navigate to dashboard and wait for network idle
  await page.goto('http://localhost:3001/dashboard', { waitUntil: 'networkidle' });
  await page.waitForTimeout(1000);

  // Save screenshot
  const outPath = 'scripts/dashboard.png';
  await page.screenshot({ path: outPath, fullPage: true });
  console.log('Saved screenshot to', outPath);

  await browser.close();
})();
