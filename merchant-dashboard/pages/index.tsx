import { useEffect } from 'react';

export default function Home() {
  useEffect(() => {
    // Redirect to static HTML file
    if (typeof window !== 'undefined') {
      window.location.href = '/index.html';
    }
  }, []);

  return <div>Loading webshop...</div>;
}
