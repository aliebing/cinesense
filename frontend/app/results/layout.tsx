import type { Metadata } from "next";

/** The result page shows one visitor's search (kept in the browser): nothing for search engines. */
export const metadata: Metadata = { title: "Search results", robots: { index: false, follow: true } };

export default function ResultsLayout({ children }: { children: React.ReactNode }) {
  return children;
}
