"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

export const ADMIN_PAGES = [
  { href: "/admin/tech", label: "Tech" },
  { href: "/admin/visitors", label: "Visitors" },
  { href: "/admin/evaluation", label: "Evaluation" },
];

export default function AdminNav({ onSignOut }: { onSignOut?: () => void }) {
  const path = usePathname();
  return (
    <header className="admin-head">
      <strong>CineSense admin</strong>
      <nav aria-label="Admin pages">
        {ADMIN_PAGES.map((p) => (
          <Link key={p.href} href={p.href} aria-current={path?.startsWith(p.href) ? "page" : undefined}>
            {p.label}
          </Link>
        ))}
      </nav>
      <Link href="/" className="admin-back">
        Back to the app
      </Link>
      {onSignOut && (
        <button type="button" className="admin-signout" onClick={onSignOut}>
          Sign out
        </button>
      )}
    </header>
  );
}
