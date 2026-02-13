import { useEffect, useState } from 'react';

export default function Webshop() {
  const [html, setHtml] = useState('');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch('/api/webshop?page=index')
      .then(res => res.text())
      .then(data => {
        setHtml(data);
        setLoading(false);
      })
      .catch(err => {
        console.error('Failed to load webshop:', err);
        setLoading(false);
      });
  }, []);

  if (loading) return <div>Loading...</div>;

  return (
    <div dangerouslySetInnerHTML={{ __html: html }} />
  );
}

export const config = {
  revalidate: 3600,
};
