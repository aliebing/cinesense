/**
 * Realistic theatre curtain drawn as SVG: velvet folds that hang straight at the top,
 * converge towards the outer edge where an antique-gold rope tie-back with a tassel holds them,
 * and flare out again below. The fabric stretches with the curtain; the tie-back keeps its proportions.
 */

const W = 200; // fabric viewBox width (outer edge at x = 0)
const H = 1000;
const TIE_Y = 760;
const FOLDS = 12;

// x positions of the fold edges at the top, at the tie and at the floor (outer edge = 0)
const edge = (i: number) => {
  const t = i / FOLDS;
  return { top: t * W, tie: t * 64, floor: t * 108 };
};

function foldPath(i: number): string {
  const a = edge(i);
  const b = edge(i + 1);
  // each edge: straight-ish drop from the top, curving into the gather, then flaring to the floor
  const down = (e: ReturnType<typeof edge>) =>
    `C ${e.top} ${TIE_Y * 0.45}, ${e.tie + (e.top - e.tie) * 0.35} ${TIE_Y * 0.8}, ${e.tie} ${TIE_Y} ` +
    `C ${e.tie} ${TIE_Y + 90}, ${e.floor} ${H - 120}, ${e.floor} ${H}`;
  const up = (e: ReturnType<typeof edge>) =>
    `C ${e.floor} ${H - 120}, ${e.tie} ${TIE_Y + 90}, ${e.tie} ${TIE_Y} ` +
    `C ${e.tie + (e.top - e.tie) * 0.35} ${TIE_Y * 0.8}, ${e.top} ${TIE_Y * 0.45}, ${e.top} 0`;
  return `M ${a.top} 0 ${down(a)} L ${b.floor} ${H} ${up(b)} Z`;
}

const FOLD_PATHS = Array.from({ length: FOLDS }, (_, i) => foldPath(i));

export function CurtainFabric({ side }: { side: "left" | "right" }) {
  const id = `curtain-${side}`;
  return (
    <svg
      className="curtain-fabric"
      viewBox={`0 0 ${W} ${H}`}
      preserveAspectRatio="none"
      aria-hidden="true"
      style={side === "right" ? { transform: "scaleX(-1)" } : undefined}
    >
      <defs>
        {/* one fold: deep shadow in the valley, a soft highlight on the crest */}
        <linearGradient id={`${id}-fold`} x1="0" y1="0" x2="1" y2="0">
          <stop offset="0" stopColor="#2a0309" />
          <stop offset=".22" stopColor="#5e0a17" />
          <stop offset=".5" stopColor="#a3172b" />
          <stop offset=".62" stopColor="#c0283b" />
          <stop offset=".8" stopColor="#6d0d1a" />
          <stop offset="1" stopColor="#2a0309" />
        </linearGradient>
        <linearGradient id={`${id}-shade`} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stopColor="#000" stopOpacity=".75" />
          <stop offset=".12" stopColor="#000" stopOpacity="0" />
          <stop offset=".7" stopColor="#000" stopOpacity="0" />
          <stop offset=".76" stopColor="#000" stopOpacity=".35" />
          <stop offset=".8" stopColor="#000" stopOpacity="0" />
          <stop offset="1" stopColor="#000" stopOpacity=".7" />
        </linearGradient>
        <radialGradient id={`${id}-sheen`} cx=".75" cy=".18" r=".7">
          <stop offset="0" stopColor="#ffb98a" stopOpacity=".22" />
          <stop offset="1" stopColor="#ffb98a" stopOpacity="0" />
        </radialGradient>
        {/* fine velvet grain */}
        <filter id={`${id}-velvet`} x="0" y="0" width="100%" height="100%">
          <feTurbulence type="fractalNoise" baseFrequency="0.9 0.012" numOctaves="2" seed="7" result="n" />
          <feColorMatrix
            in="n"
            type="matrix"
            values="0 0 0 0 0  0 0 0 0 0  0 0 0 0 0  0 0 0 0.35 0"
          />
          <feComposite in2="SourceGraphic" operator="in" />
        </filter>
        <clipPath id={`${id}-clip`}>
          {FOLD_PATHS.map((d, i) => (
            <path key={i} d={d} />
          ))}
        </clipPath>
      </defs>

      <g clipPath={`url(#${id}-clip)`}>
        {FOLD_PATHS.map((d, i) => (
          <path key={i} d={d} fill={`url(#${id}-fold)`} />
        ))}
        <rect width={W} height={H} filter={`url(#${id}-velvet)`} fill="#000" />
        <rect width={W} height={H} fill={`url(#${id}-shade)`} />
        <rect width={W} height={H} fill={`url(#${id}-sheen)`} />
      </g>
    </svg>
  );
}

/** Antique-gold twisted rope tie-back with a tassel. */
export function TieBack({ side }: { side: "left" | "right" }) {
  const id = `tie-${side}`;
  return (
    <svg
      className="curtain-tie"
      viewBox="0 0 120 150"
      aria-hidden="true"
      style={side === "right" ? { transform: "scaleX(-1)" } : undefined}
    >
      <defs>
        <linearGradient id={`${id}-gold`} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stopColor="#f6e2a8" />
          <stop offset=".35" stopColor="#c99a45" />
          <stop offset=".7" stopColor="#8a6122" />
          <stop offset="1" stopColor="#4f3510" />
        </linearGradient>
        <linearGradient id={`${id}-tassel`} x1="0" y1="0" x2="1" y2="0">
          <stop offset="0" stopColor="#6e4b17" />
          <stop offset=".45" stopColor="#d9b061" />
          <stop offset=".6" stopColor="#f0d48e" />
          <stop offset="1" stopColor="#6e4b17" />
        </linearGradient>
      </defs>
      {/* rope wrapping the gathered folds */}
      <path d="M -4 26 Q 50 40 92 28" stroke="#2d1d07" strokeWidth="13" fill="none" strokeLinecap="round" opacity=".55" />
      <path d="M -4 22 Q 50 36 92 24" stroke={`url(#${id}-gold)`} strokeWidth="11" fill="none" strokeLinecap="round" />
      <path
        d="M -4 22 Q 50 36 92 24"
        stroke="#4f3510"
        strokeWidth="11"
        strokeDasharray="2.2 4.4"
        fill="none"
        opacity=".55"
      />
      {/* knot and tassel */}
      <path d="M 92 24 C 98 40, 92 52, 96 62" stroke={`url(#${id}-gold)`} strokeWidth="5" fill="none" />
      <ellipse cx="96" cy="66" rx="9" ry="7" fill={`url(#${id}-gold)`} stroke="#4f3510" strokeWidth="1" />
      <path d="M 90 72 Q 96 69 102 72 L 104 80 Q 96 83 88 80 Z" fill={`url(#${id}-gold)`} stroke="#4f3510" strokeWidth=".8" />
      <path d="M 88 80 Q 96 84 104 80 L 112 136 Q 96 144 80 136 Z" fill={`url(#${id}-tassel)`} />
      <g stroke="#5a3d12" strokeWidth=".7" opacity=".7">
        {[84, 88, 92, 96, 100, 104, 108].map((x) => (
          <line key={x} x1={x > 96 ? 96 + (x - 96) * 0.45 : 96 - (96 - x) * 0.45} y1="82" x2={x} y2="138" />
        ))}
      </g>
      <path d="M 82 132 Q 96 140 110 132" stroke="#f0d48e" strokeWidth="1.2" fill="none" opacity=".6" />
    </svg>
  );
}
