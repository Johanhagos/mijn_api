import { NextApiRequest, NextApiResponse } from 'next';
import fs from 'fs';
import path from 'path';

export default function handler(req: NextApiRequest, res: NextApiResponse) {
  const { page = 'index' } = req.query;
  
  try {
    // Sanitize page name to prevent directory traversal
    const safePage = String(page).replace(/\.\./g, '').replace(/\//g, '');
    const filePath = path.join(process.cwd(), 'public', `${safePage}.html`);
    
    if (fs.existsSync(filePath)) {
      const html = fs.readFileSync(filePath, 'utf-8');
      res.setHeader('Content-Type', 'text/html');
      res.status(200).send(html);
    } else {
      res.status(404).json({ error: 'Page not found' });
    }
  } catch (error) {
    res.status(500).json({ error: 'Failed to load page' });
  }
}
