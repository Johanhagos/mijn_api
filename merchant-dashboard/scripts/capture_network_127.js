const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

(async () => {
  const outDir = path.resolve(__dirname, '..', 'logs');
  if (!fs.existsSync(outDir)) fs.mkdirSync(outDir, { recursive: true });
  const networkLogPath = path.join(outDir, 'network_log_127.json');
  const consoleLogPath = path.join(outDir, 'console_log_127.txt');

  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext();
  const page = await context.newPage();

  const logs = { requests: [], responses: [], failed: [], console: [] };

  page.on('request', (req) => {
    try {
      logs.requests.push({
        url: req.url(),
        method: req.method(),
        headers: req.headers(),
        postData: req.postData(),
        timestamp: Date.now(),
      });
    } catch (e) {}
  });

  page.on('response', async (res) => {
    try {
      const body = await res.text().catch(() => null);
      logs.responses.push({
        url: res.url(),
        status: res.status(),
        headers: res.headers(),
        body: body && body.length > 10000 ? body.slice(0, 10000) + '\n[truncated]' : body,
        timestamp: Date.now(),
      });
    } catch (e) {}
  });

  page.on('requestfailed', (rf) => {
    try {
      const f = rf.failure || {};
      logs.failed.push({ url: rf.url(), errorText: f.errorText || f.message || null, timestamp: Date.now() });
    } catch (e) {}
  });

  page.on('console', (msg) => {
    try {
      logs.console.push({ type: msg.type(), text: msg.text(), location: msg.location(), timestamp: Date.now() });
    } catch (e) {}
  });

  try {
    await page.goto('http://127.0.0.1:3001/login', { waitUntil: 'networkidle', timeout: 20000 });
    await page.fill('input[type="email"]', 'merchant_test@example.com').catch(() => {});
    await page.fill('input[type="password"]', 'merchant123').catch(() => {});
    await page.click('button:has-text("Login")').catch(() => {});
    try {
      await page.waitForURL('**/dashboard', { timeout: 20000 });
    } catch (e) {
      await page.waitForTimeout(2000);
    }
  } catch (e) {
    logs.failed.push({ url: 'navigation', errorText: String(e), timestamp: Date.now() });
  }

  fs.writeFileSync(networkLogPath, JSON.stringify(logs, null, 2), 'utf8');
  const consoleText = logs.console.map(c => `[${new Date(c.timestamp).toISOString()}] ${c.type}: ${c.text}`).join('\n');
  fs.writeFileSync(consoleLogPath, consoleText, 'utf8');

  await browser.close();
  console.log('network and console logs saved to', outDir);
})();
