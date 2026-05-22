/** @type {import('next').NextConfig} */
const apiProxyBase = process.env.NEXT_PUBLIC_API_PROXY_BASE || "http://localhost:8000";

const nextConfig = {
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: `${apiProxyBase}/api/:path*`,
      },
    ];
  },
};

module.exports = nextConfig;
