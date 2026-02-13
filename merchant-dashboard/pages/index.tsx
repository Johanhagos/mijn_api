import { readFileSync } from 'fs';
import { join } from 'path';
import { useEffect } from 'react';
import { useRouter } from 'next/router';

interface Props {
  html: string;
}

export default function Home({ html }: Props) {
  const router = useRouter();

  useEffect(() => {
    // If accessed via dashboard subdomain, redirect to login
    if (typeof window !== 'undefined' && window.location.hostname === 'dashboard.apiblockchain.io') {
      router.push('/login');
    }
  }, [router]);

  return (
    <div
      style={{ width: '100%' }}
      dangerouslySetInnerHTML={{ __html: html }}
    />
  );
}

export async function getStaticProps() {
  try {
    const filePath = join(process.cwd(), 'public', 'index.html');
    const html = readFileSync(filePath, 'utf-8');
    
    return {
      props: { html },
      revalidate: 3600,
    };
  } catch (error) {
    console.error('Error reading HTML:', error);
    return {
      notFound: true,
    };
  }
}
