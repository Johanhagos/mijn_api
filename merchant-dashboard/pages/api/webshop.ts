import { NextApiRequest, NextApiResponse } from 'next';

export default async function handler(req: NextApiRequest, res: NextApiResponse) {
  const { page = 'index' } = req.query;
  
  try {
    // Sanitize page name
    const safePage = String(page).replace(/\.\./g, '').replace(/\//g, '');
    
    // Fetch the HTML file from public folder via relative URL
    const htmlUrl = `${process.env.NEXT_PUBLIC_SITE_URL || 'https://apiblockchain.io'}/${safePage}.html`;
    
    const response = await fetch(htmlUrl);
    if (!response.ok) {
      return res.status(404).json({ error: 'Page not found' });
    }
    
    const html = await response.text();
    res.setHeader('Content-Type', 'text/html; charset=utf-8');
    res.status(200).send(html);
  } catch (error) {
    res.status(500).json({ error: 'Failed to load page' });
  }
}
