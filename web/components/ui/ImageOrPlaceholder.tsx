"use client";

import { useState } from "react";

type Props = { src: string | null; alt: string; className?: string };

/** Film image with a styled dark fallback when the URL is missing or fails to load. */
export default function ImageOrPlaceholder({ src, alt, className = "" }: Props) {
  const [failed, setFailed] = useState(false);
  if (!src || failed) {
    return (
      <div data-testid="image-placeholder" role="img" aria-label={alt} className={`img-placeholder ${className}`}>
        <span aria-hidden="true">🎬</span>
      </div>
    );
  }
  return (
    // eslint-disable-next-line @next/next/no-img-element -- external TMDB/picsum images, sized by CSS
    <img src={src} alt={alt} className={`img-cover ${className}`} onError={() => setFailed(true)} draggable={false} />
  );
}
