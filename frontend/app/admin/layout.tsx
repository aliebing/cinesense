import type { Metadata } from "next";
import AdminNav from "@/components/admin/AdminNav";
import "./admin.css";

export const metadata: Metadata = { title: "CineSense admin" };

/** The operator's area behind TECH_USER / TECH_PASSWORD (proxy.ts; the backend checks the same login):
 *  the technical view of one turn, the visitor log and the evaluation. Deliberately plain, no effects. */
export default function AdminLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <div className="tech">
      <AdminNav />
      <main>{children}</main>
    </div>
  );
}
