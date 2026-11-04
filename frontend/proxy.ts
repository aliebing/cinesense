import { type NextRequest, NextResponse } from "next/server";
import { basicAuthOk } from "@/lib/basicAuth";

/** The technical view shows prompts, tool calls and costs: it needs the login from TECH_USER / TECH_PASSWORD.
 *  The browser then sends the same login with /api/inspect, which the backend checks as well. */
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
  matcher: ["/tech", "/tech/:path*"],
};
