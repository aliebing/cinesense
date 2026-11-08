/** The operator's sign-in for /admin (backend/cinesense/web_api/admin_session.py): name + password, then an
 *  HttpOnly session cookie the browser sends with every admin call. Results carry only the HTTP status
 *  (0 = no connection). */

const BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export type AdminResult = { ok: true; name: string } | { ok: false; status: number };

async function call(path: string, init: RequestInit = {}): Promise<AdminResult> {
  let res: Response;
  try {
    res = await fetch(`${BASE_URL}/api/admin${path}`, { cache: "no-store", credentials: "include", ...init });
  } catch {
    return { ok: false, status: 0 };
  }
  if (!res.ok) return { ok: false, status: res.status };
  const body = (await res.json().catch(() => ({}))) as { name?: string };
  return { ok: true, name: body.name ?? "" };
}

const post = (body?: unknown): RequestInit => ({
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: body === undefined ? undefined : JSON.stringify(body),
});

export const adminMe = () => call("/me");
export const adminLogin = (name: string, password: string) => call("/login", post({ name, password }));
export const adminLogout = () => call("/logout", post());

export function adminErrorText(status: number): string {
  if (status === 401) return "Name or password is wrong.";
  if (status === 429) return "Too many attempts. Please wait 15 minutes and try again.";
  if (status === 0) return "The server cannot be reached.";
  return `Sign-in failed (error ${status}).`;
}
