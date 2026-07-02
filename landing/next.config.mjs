/** @type {import('next').NextConfig} */
const nextConfig = {
  // Hosted natively on Vercel (standard Next.js app): the landing page is statically
  // generated and the console route is client-only. No `output: 'export'` so Vercel serves
  // it directly (that setting writes to out/ and can 404 on Vercel).
  images: {
    unoptimized: true,
  },
  reactStrictMode: true,
};

export default nextConfig;
