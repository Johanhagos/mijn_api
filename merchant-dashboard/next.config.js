/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  env: {
    NEXT_PUBLIC_API_URL: 'https://api.apiblockchain.io',
  },
  // Ensure static files in public are served correctly
  publicRuntimeConfig: {
    basePath: '',
  },
  // Revert index back to showing dashboard
  async rewrites() {
    return {
      beforeFiles: [
        // Serve webshop pages from public folder
        {
          source: '/index.html',
          destination: '/api/serve-webshop?page=index',
        },
        {
          source: '/:page(about|services|contact|booking|quotation).html',
          destination: '/api/serve-webshop?page=:page',
        },
      ],
    };
  },
};

module.exports = nextConfig;
