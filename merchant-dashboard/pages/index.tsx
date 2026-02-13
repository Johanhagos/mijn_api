import { GetStaticProps } from 'next';
import fs from 'fs';
import path from 'path';

interface Props {
  html: string;
}

export default function Index({ html }: Props) {
  return (
    <div
      style={{ width: '100%', minHeight: '100vh' }}
      dangerouslySetInnerHTML={{ __html: html }}
    />
  );
}

export const getStaticProps: GetStaticProps = async () => {
  try {
    const filePath = path.join(process.cwd(), 'public', 'index.html');
    const html = fs.readFileSync(filePath, 'utf-8');
    
    return {
      props: { html },
      revalidate: 3600,
    };
  } catch (error) {
    console.error('Failed to load HTML:', error);
    return {
      notFound: true,
    };
  }
};
