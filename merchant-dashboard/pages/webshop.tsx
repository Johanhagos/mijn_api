import { useEffect, useState } from 'react';

export default function Webshop() {
  const [html, setHtml] = useState('');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Fetch the static HTML file directly from public folder
    fetch('/index.html')
      .then(res => {
        if (!res.ok) throw new Error('Failed to load');
        return res.text();
      })
      .then(data => {
        setHtml(data);
        setLoading(false);
      })
      .catch(err => {
        console.error('Failed to load webshop:', err);
        setLoading(false);
      });
  }, []);

  if (loading) return <div style={{ padding: '20px' }}>Loading webshop...</div>;
  if (!html) return <div style={{ padding: '20px' }}>Failed to load webshop</div>;

  return (
    <div dangerouslySetInnerHTML={{ __html: html }} />
  );
}
