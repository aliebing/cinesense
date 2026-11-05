import { type NextRequest, NextResponse } from "next/server";
import { basicAuthOk } from "@/lib/basicAuth";

/** The admin area (technical view, visitor log, evaluation) shows prompts, chats and costs: it needs the login
 *  from TECH_USER / TECH_PASSWORD. The browser then sends the same login with the /api calls behind it
 *  (/api/inspect, /api/admin/*, /api/eval/*), which the backend checks as well. */
export function proxy(request: NextRequest) {
  if (basicAuthOk(request.headers.get("authorization"), process.env.TECH_USER, process.env.TECH_PASSWORD)) {
    return NextResponse.next();
  }
  return new NextResponse("Login required", {
    status: 401,
    headers: { "WWW-Authenticate": 'Basic realm="CineSense tech", charset="UTF-8"' },
  });
}

export const config = {
  matcher: ["/admin", "/admin/:path*", "/tech", "/tech/:path*"],
};
