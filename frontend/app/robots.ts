import type { MetadataRoute } from "next";
import { SITE_URL } from "@/lib/seo";

/** Personal search results and the operator's area stay out of search engines. */
export default function robots(): MetadataRoute.Robots {
  return {
    rules: { userAgent: "*", allow: "/", disallow: ["/admin", "/tech", "/api/", "/results"] },
    sitemap: `${SITE_URL}/sitemap.xml`,
    host: SITE_URL,
  };
}
