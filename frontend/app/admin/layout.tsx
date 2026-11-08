import type { Metadata } from "next";
import AdminGate from "@/components/admin/AdminGate";
import "./admin.css";

export const metadata: Metadata = { title: { absolute: "CineSense admin" }, robots: { index: false, follow: false } };

/** The operator's area behind its own sign-in (TECH_USER / TECH_PASSWORD, session cookie; the backend checks it):
 *  the technical view of one turn, the visitor log and the evaluation. Deliberately plain, no effects. */
export default function AdminLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <div className="tech">
      <AdminGate>{children}</AdminGate>
    </div>
  );
}
