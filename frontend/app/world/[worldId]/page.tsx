import type { Metadata } from "next";
import { Suspense } from "react";
import CinemaFrame from "@/components/cinema/CinemaFrame";
import GenreView from "@/components/genre/GenreView";
import { worldSeo } from "@/lib/seo";

type RouteProps = {
  params: Promise<{ worldId: string }>;
  searchParams: Promise<{ film?: string | string[]; from?: string | string[] }>;
};

export async function generateMetadata({ params }: Pick<RouteProps, "params">): Promise<Metadata> {
  const { worldId } = await params;
  const w = worldSeo(worldId);
  if (!w) return { title: "Mood world", robots: { index: false } };
  const description = `Find ${w.about} by mood, to stream in Germany or see in cinemas. Every pick says why it fits.`;
  return {
    title: `${w.title} films`,
    description,
    alternates: { canonical: `/world/${w.id}` },
    // a page's own openGraph replaces the inherited one, so the shared preview image is named again
    openGraph: { title: `${w.title} films · CineSense`, description, url: `/world/${w.id}`, images: ["/opengraph-image"] },
    twitter: { title: `${w.title} films · CineSense`, description, images: ["/opengraph-image"] },
  };
}

async function GenreRoute({ params, searchParams }: RouteProps) {
  const { worldId } = await params;
  const { film, from } = await searchParams;
  return <GenreView worldId={worldId} filmId={typeof film === "string" ? film : null} fromSearch={from === "search"} />;
}

// Runtime params are read inside <Suspense> so the frame can be prerendered (Next 16 instant navigation).
export default function GenrePage(props: RouteProps) {
  return (
    <Suspense
      fallback={
        <CinemaFrame>
          <p className="genre-loading">Loading …</p>
        </CinemaFrame>
      }
    >
      <GenreRoute {...props} />
    </Suspense>
  );
}
