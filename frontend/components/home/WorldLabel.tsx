import Link from "next/link";
import type { MoodWorld } from "@/lib/types";

export default function WorldLabel({ world, href }: { world: MoodWorld; href: string }) {
  return (
    <div className="world-label">
      <div className="world-label__kicker">{world.kicker}</div>
      <b>{world.title}</b>
      <Link href={href}>Enter world →</Link>
    </div>
  );
}
