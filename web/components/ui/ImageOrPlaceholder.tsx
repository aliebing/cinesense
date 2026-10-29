"use client";

import { useState } from "react";

type Props = { src: string | null; alt: string; className?: string };

/** Film image with a styled dark fallback when the URL is missing or fails to load. */
export default function ImageOrPlaceholder({ src, alt, className = "" }: Props) {
  // Remember which src failed, so a new src gets a fresh attempt.
  const [failedSrc, setFailedSrc] = useState<string | null>(null);
  if (!src || failedSrc === src) {
    return (
      <div data-testid="image-placeholder" role="img" aria-label={alt} className={`img-placeholder ${className}`}>
        <span aria-hidden="true">🎬</span>
      </div>
    );
  }
  return (
    // eslint-disable-next-line @next/next/no-img-element -- external TMDB/picsum images, sized by CSS
    <img src={src} alt={alt} className={`img-cover ${className}`} onError={() => setFailedSrc(src)} draggable={false} />
  );
}
