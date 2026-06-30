/** @type {import('next').NextConfig} */
const nextConfig = {
  output: 'standalone',
  poweredByHeader: false,
  typedRoutes: false,
  turbopack: {
    root: process.cwd()
  }
};
export default nextConfig;
