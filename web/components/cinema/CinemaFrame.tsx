import type { ReactNode } from "react";
import { CurtainFabric, TieBack } from "@/components/cinema/Curtain";

/**
 * Cinema screen: matte-black room, letterbox bars above and below (always present),
 * a wide stage, and velvet curtains gathered near the bottom by an antique-gold tie-back.
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
        <CurtainFabric side="left" />
        <TieBack side="left" />
      </div>
      <div className="cinema-curtain cinema-curtain--right" data-testid="curtain" aria-hidden="true">
        <CurtainFabric side="right" />
        <TieBack side="right" />
      </div>
    </div>
  );
}
