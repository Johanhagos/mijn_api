import type { NextApiRequest, NextApiResponse } from 'next'

import { API_BASE } from '../../lib/config'

export default async function handler(req: NextApiRequest, res: NextApiResponse) {
  if (req.method !== 'POST') {
    res.status(405).end()
    return
  }

  try {
    const backendRes = await fetch(`${API_BASE}/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(req.body),
      // forward cookies (if any) from client
      credentials: 'include',
    })

    const text = await backendRes.text()

    // Forward Set-Cookie if backend set it (refresh token)
    const sc = backendRes.headers.get('set-cookie')
    if (sc) {
      res.setHeader('Set-Cookie', sc)
    }

    res.status(backendRes.status).send(text)
  } catch (err: any) {
    res.status(502).json({ error: String(err) })
  }
}
