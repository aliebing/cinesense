import type { ReactNode } from "react";

/** Small gold bow that ties the curtain back near the bottom. */
function TieBack() {
  return (
    <svg className="cinema-tie" viewBox="0 0 64 40" aria-hidden="true">
      <defs>
        <linearGradient id="cinema-gold" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0" stopColor="#fff1c2" />
          <stop offset=".45" stopColor="#f3c76b" />
          <stop offset="1" stopColor="#9a6a1c" />
        </linearGradient>
      </defs>
      <path d="M32 18 C20 4 6 6 8 16 C10 26 22 24 32 18 Z" fill="url(#cinema-gold)" />
      <path d="M32 18 C44 4 58 6 56 16 C54 26 42 24 32 18 Z" fill="url(#cinema-gold)" />
      <path d="M29 20 L20 38 L26 36 L31 24 Z" fill="url(#cinema-gold)" />
      <path d="M35 20 L44 38 L38 36 L33 24 Z" fill="url(#cinema-gold)" />
      <circle cx="32" cy="19" r="5" fill="url(#cinema-gold)" stroke="#7a5212" strokeWidth=".8" />
    </svg>
  );
}

/**
 * Cinema screen: matte-black room, letterbox bars above and below (always present),
 * a wide stage, and solid red curtains gathered near the bottom with a gold tie-back.
 */
export default function CinemaFrame({ children }: { children: ReactNode }) {
  return (
    <div className="cinema-room">
      <div className="cinema-letterbox" data-testid="letterbox" aria-hidden="true" />
      <div className="cinema-stage-wrap">
        <div className="cinema-stage" data-testid="cinema-stage">
          {children}
          <div className="cinema-vignette" aria-hidden="true" />
        </div>
      </div>
      <div className="cinema-letterbox" data-testid="letterbox" aria-hidden="true" />
      <div className="cinema-curtain cinema-curtain--left" data-testid="curtain" aria-hidden="true">
        <TieBack />
      </div>
      <div className="cinema-curtain cinema-curtain--right" data-testid="curtain" aria-hidden="true">
        <TieBack />
      </div>
    </div>
  );
}
