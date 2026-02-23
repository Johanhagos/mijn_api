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
    const slugParts = (params?.slug as string[]) || [];
    // If no slug provided, serve the index page
    let slug = slugParts.length > 0 ? slugParts.join('/') : 'index';

    // If the slug already contains a .html extension, don't append another
    let filename = slug.endsWith('.html') ? slug : `${slug}.html`;

    const filePath = join(process.cwd(), 'public', filename);
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
