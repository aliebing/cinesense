import type { MetadataRoute } from "next";
import { SITE_URL, WORLD_SEO } from "@/lib/seo";

export default function sitemap(): MetadataRoute.Sitemap {
  return [
    { url: SITE_URL, changeFrequency: "daily", priority: 1 },
    ...WORLD_SEO.map((w) => ({ url: `${SITE_URL}/world/${w.id}`, changeFrequency: "daily" as const, priority: 0.8 })),
    { url: `${SITE_URL}/credits`, changeFrequency: "monthly", priority: 0.3 },
    { url: `${SITE_URL}/impressum`, changeFrequency: "yearly", priority: 0.1 },
    { url: `${SITE_URL}/datenschutz`, changeFrequency: "yearly", priority: 0.1 },
  ];
}
