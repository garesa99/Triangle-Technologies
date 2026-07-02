/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  // Everything is client-rendered off the WS/REST; no server data fetching at build time.
};

export default nextConfig;
