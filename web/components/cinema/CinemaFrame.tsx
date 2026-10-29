import type { ReactNode } from "react";

/**
 * Cinema screen: matte-black room, letterbox bars above and below (always present),
 * a full-width stage, and photographed velvet curtains (narrowing towards the floor) in front of its edges.
 * Curtain photo: cottonbro studio on Pexels, cut out, tapered and colour-graded (public/curtain.webp).
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
        {/* eslint-disable-next-line @next/next/no-img-element -- decorative static image, sized by CSS */}
        <img className="curtain-photo" src="/curtain.webp" alt="" draggable={false} />
      </div>
      <div className="cinema-curtain cinema-curtain--right" data-testid="curtain" aria-hidden="true">
        {/* eslint-disable-next-line @next/next/no-img-element -- decorative static image, sized by CSS */}
        <img className="curtain-photo" src="/curtain.webp" alt="" draggable={false} />
      </div>
    </div>
  );
}
