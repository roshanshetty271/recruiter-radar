/** @type {import('next').NextConfig} */
const nextConfig = {
  experimental: {
    optimizeCss: true,
  },
  images: {
    domains: ["avatars.githubusercontent.com", "media.licdn.com"],
  },
};

module.exports = nextConfig;
