import { GetStaticProps, GetStaticPaths } from 'next';
import fs from 'fs';
import path from 'path';

export default function StaticPage({ html }: { html: string }) {
  return <div dangerouslySetInnerHTML={{ __html: html }} />;
}

export const getStaticPaths: GetStaticPaths = async () => {
  return {
    paths: [],
    fallback: 'blocking',
  };
};

export const getStaticProps: GetStaticProps = async ({ params }) => {
  const slug = Array.isArray(params?.slug) ? params.slug.join('/') : params?.slug || '';
  
  // Try to find HTML file in public directory
  const publicPath = path.join(process.cwd(), 'public', `${slug}.html`);
  const indexPath = path.join(process.cwd(), 'public', slug, 'index.html');
  
  let htmlContent = '';
  
  // Check if it's a direct HTML file
  if (fs.existsSync(publicPath)) {
    htmlContent = fs.readFileSync(publicPath, 'utf-8');
  }
  // Check if it's a directory with index.html
  else if (fs.existsSync(indexPath)) {
    htmlContent = fs.readFileSync(indexPath, 'utf-8');
  }
  // If root path, serve public/index.html
  else if (slug === '' || slug === '/') {
    const rootPath = path.join(process.cwd(), 'public', 'index.html');
    if (fs.existsSync(rootPath)) {
      htmlContent = fs.readFileSync(rootPath, 'utf-8');
    }
  }
  
  if (!htmlContent) {
    return {
      notFound: true,
      revalidate: 60,
    };
  }
  
  return {
    props: { html: htmlContent },
    revalidate: 60,
  };
};
