const basePath = process.env.NEXT_PUBLIC_BASE_PATH || '';

/** @type {import('next').NextConfig} */
const nextConfig = {
  output: 'standalone',
  poweredByHeader: false,
  typedRoutes: false,
  basePath,
  assetPrefix: basePath || undefined,
  turbopack: {
    root: process.cwd()
  }
};

export default nextConfig;
