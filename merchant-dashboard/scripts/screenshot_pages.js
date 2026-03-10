const fs = require('fs');
const path = require('path');
const { chromium } = require('playwright');

(async () => {
  const base = process.env.BASE_URL || 'http://localhost:3000';
  const outDir = path.join(__dirname, '..', 'screenshots');
  if (!fs.existsSync(outDir)) fs.mkdirSync(outDir, { recursive: true });

  // Pages discovered from .next/server/pages (HTML files)
  const pages = [
    '/',
    '/index',
    '/contact',
    '/contact.html',
    '/quotation',
    '/quotation.html',
    '/dashboard',
    '/invoices',
    '/login',
    '/about',
    '/services',
    '/signup',
    '/plugin-setup',
    '/api-keys'
  ];

  const browser = await chromium.launch({ args: ['--no-sandbox'] });
  const context = await browser.newContext({ viewport: { width: 1280, height: 900 } });
  const page = await context.newPage();

  for (const p of pages) {
    try {
      const url = base.replace(/\/$/, '') + (p.startsWith('/') ? p : '/' + p);
      console.log('Visiting', url);
      const res = await page.goto(url, { waitUntil: 'networkidle', timeout: 15000 });
      if (!res || res.status() >= 400) {
        console.log('Warning: non-OK response', res && res.status());
      }
      // Wait a short time for client JS hydration
      await page.waitForTimeout(800);
      const safeName = p.replace(/[\/\[\]\.:]/g, '_').replace(/^_+/, '') || 'root';
      const outPath = path.join(outDir, `${safeName}.png`);
      await page.screenshot({ path: outPath, fullPage: true });
      console.log('Saved', outPath);
    } catch (err) {
      console.error('Failed to capture', p, err.message);
    }
  }

  await browser.close();
  console.log('Done');
})();
