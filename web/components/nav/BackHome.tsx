import Link from "next/link";

/** Back to the start page, which keeps the conversation and shows the search hits in its rows. */
export default function BackHome() {
  return (
    <Link href="/" className="back-home" data-testid="back-home">
      ← Back to results
    </Link>
  );
}
