import Link from "next/link";
import type { MoodWorld } from "@/lib/types";

export default function WorldLabel({ world, href }: { world: MoodWorld; href: string }) {
  return (
    <div className="world-label">
      <div className="world-label__kicker">{world.kicker}</div>
      <b>{world.title_de}</b>
      <Link href={href}>Welt betreten →</Link>
    </div>
  );
}
