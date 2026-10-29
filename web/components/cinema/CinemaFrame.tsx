import type { ReactNode } from "react";

/**
 * Cinema screen: matte-black room, letterbox bars above and below (always present),
 * the largest Cinemascope (2.39:1) stage that fits, and narrow velvet curtain hints at its edges.
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
      <div className="cinema-curtain cinema-curtain--left" data-testid="curtain" aria-hidden="true" />
      <div className="cinema-curtain cinema-curtain--right" data-testid="curtain" aria-hidden="true" />
    </div>
  );
}
