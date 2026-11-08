"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import AdminNav from "@/components/admin/AdminNav";
import { adminErrorText, adminLogin, adminLogout, adminMe } from "@/lib/admin";

type Gate = "checking" | "login" | "ok" | { status: number };

/** Shows the admin pages only after sign-in; otherwise the sign-in form (as in HikeSense's /backend). */
export default function AdminGate({ children }: { children: React.ReactNode }) {
  const [gate, setGate] = useState<Gate>("checking");
  const [attempt, setAttempt] = useState(0); // bumped after sign-in / sign-out: check the session again

  useEffect(() => {
    let live = true;
    void adminMe().then((r) => {
      if (live) setGate(r.ok ? "ok" : r.status === 401 ? "login" : { status: r.status });
    });
    return () => {
      live = false;
    };
  }, [attempt]);

  if (gate === "checking") return null;
  if (gate === "login") return <AdminLogin onSignedIn={() => setAttempt((n) => n + 1)} />;
  if (typeof gate === "object") return <p className="tech-error">{adminErrorText(gate.status)}</p>;
  return (
    <>
      <AdminNav onSignOut={() => void adminLogout().finally(() => setAttempt((n) => n + 1))} />
      <main>{children}</main>
    </>
  );
}

function AdminLogin({ onSignedIn }: { onSignedIn: () => void }) {
  const [name, setName] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  return (
    <main className="admin-login">
      <h1>CineSense admin</h1>
      <form
        onSubmit={async (ev) => {
          ev.preventDefault();
          setBusy(true);
          setError(null);
          const r = await adminLogin(name, password);
          setBusy(false);
          if (r.ok) return onSignedIn();
          setError(adminErrorText(r.status));
        }}
      >
        <label>
          Name
          <input type="text" required autoComplete="username" value={name} onChange={(e) => setName(e.target.value)} />
        </label>
        <label>
          Password
          <input
            type="password"
            required
            autoComplete="current-password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
          />
        </label>
        {error && (
          <p role="alert" className="tech-error">
            {error}
          </p>
        )}
        <button type="submit" disabled={busy}>
          {busy ? "Signing in …" : "Sign in"}
        </button>
      </form>
      <Link href="/">Back to the app</Link>
    </main>
  );
}
