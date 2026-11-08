import type { Metadata } from "next";

export const metadata: Metadata = { title: "Datenschutz", alternates: { canonical: "/datenschutz" } };

export default function DatenschutzLayout({ children }: { children: React.ReactNode }) {
  return children;
}
