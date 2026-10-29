import Link from "next/link";
import CinemaFrame from "@/components/cinema/CinemaFrame";
import FogLight from "@/components/atmosphere/FogLight";

export default function NotFound() {
  return (
    <CinemaFrame>
      <FogLight tint="#1b4a6b" />
      <div className="not-found">
        <h1>Nicht gefunden</h1>
        <p>Diese Welt oder diesen Film gibt es hier nicht.</p>
        <Link href="/">Zur Startseite</Link>
      </div>
    </CinemaFrame>
  );
}
