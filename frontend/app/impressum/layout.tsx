import type { Metadata } from "next";

export const metadata: Metadata = { title: "Impressum", alternates: { canonical: "/impressum" } };

export default function ImpressumLayout({ children }: { children: React.ReactNode }) {
  return children;
}
