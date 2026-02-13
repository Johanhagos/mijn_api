import { readFileSync } from 'fs';
import { join } from 'path';

interface Props {
  html: string;
}

export default function Home({ html }: Props) {
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
