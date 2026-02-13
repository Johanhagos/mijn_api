import { readFileSync } from 'fs';
import { join } from 'path';
import { GetStaticProps, GetStaticPaths } from 'next';

interface Props {
  html: string;
}

export default function StaticPage({ html }: Props) {
  return (
    <div
      style={{ width: '100%' }}
      dangerouslySetInnerHTML={{ __html: html }}
    />
  );
}

export const getStaticPaths: GetStaticPaths = async () => {
  const routes = ['about', 'services', 'booking', 'contact', 'quotation'];
  
  return {
    paths: routes.map(route => ({ params: { slug: [route] } })),
    fallback: false,
  };
};

export const getStaticProps: GetStaticProps = async ({ params }) => {
  try {
    const slug = (params?.slug as string[])?.[0] || 'index';
    const filePath = join(process.cwd(), 'public', `${slug}.html`);
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
};
