import { Suspense } from "react";
import CinemaFrame from "@/components/cinema/CinemaFrame";
import GenreView from "@/components/genre/GenreView";

type RouteProps = {
  params: Promise<{ worldId: string }>;
  searchParams: Promise<{ film?: string | string[] }>;
};

async function GenreRoute({ params, searchParams }: RouteProps) {
  const { worldId } = await params;
  const { film } = await searchParams;
  return <GenreView worldId={worldId} filmId={typeof film === "string" ? film : null} />;
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
