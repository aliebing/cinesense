import type { Metadata } from "next";
import { connection } from "next/server";
import { Suspense } from "react";
import HomePage from "@/components/home/HomePage";
import { loadHome } from "@/lib/homeServer";

export const metadata: Metadata = { alternates: { canonical: "/" } };

/** The shell (frame, claim, chat) is static and comes at once; the film rows are fetched on the server and
 *  streamed into the same response, so the browser no longer waits for its own JavaScript before asking. */
export default function Page() {
  return (
    <Suspense fallback={<HomePage />}>
      <HomeWithRows />
    </Suspense>
  );
}

async function HomeWithRows() {
  await connection(); // per request, never at build time (the API is not there while the image builds)
  return <HomePage initial={await loadHome()} />;
}
