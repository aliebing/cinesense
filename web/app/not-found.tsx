import Link from "next/link";
import CinemaFrame from "@/components/cinema/CinemaFrame";
import FogLight from "@/components/atmosphere/FogLight";

export default function NotFound() {
  return (
    <CinemaFrame>
      <FogLight tint="#1b4a6b" />
      <div className="not-found">
        <h1>Not found</h1>
        <p>This world or film doesn’t exist here.</p>
        <Link href="/">Back to home</Link>
      </div>
    </CinemaFrame>
  );
}
