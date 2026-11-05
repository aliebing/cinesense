import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  /* config options here */
  cacheComponents: true,
  // the technical view and the evaluation moved into the admin area
  async redirects() {
    return [
      { source: "/admin", destination: "/admin/tech", permanent: false },
      { source: "/tech", destination: "/admin/tech", permanent: false },
      { source: "/tech/eval", destination: "/admin/evaluation", permanent: false },
    ];
  },
  partialPrefetching: true,
  turbopack: {
    rules: {
      "*.css": {
        loaders: ["@tailwindcss/turbopack"],
        as: "*.css",
      },
    },
  },
};

export default nextConfig;
