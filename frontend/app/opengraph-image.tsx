import { ImageResponse } from "next/og";

/** The link preview (WhatsApp, LinkedIn, Reddit …): the cinema screen between red curtains, with the claim. */
export const alt = "CineSense: Don't choose a movie. Choose a feeling.";
export const size = { width: 1200, height: 630 };
export const contentType = "image/png";

const curtain = (side: "left" | "right") => ({
  position: "absolute" as const,
  top: 0,
  bottom: 0,
  [side]: 0,
  width: 150,
  background:
    "repeating-linear-gradient(90deg, #4a0a0e 0px, #8c1a1f 18px, #b3262c 30px, #8c1a1f 42px, #4a0a0e 60px)",
});

export default function OpengraphImage() {
  return new ImageResponse(
    (
      <div
        style={{
          width: "100%",
          height: "100%",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          background: "radial-gradient(ellipse at 50% 40%, #2a2420 0%, #0b0a09 70%)",
          position: "relative",
        }}
      >
        <div style={curtain("left")} />
        <div style={curtain("right")} />
        <div
          style={{
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            justifyContent: "center",
            width: 820,
            height: 364,
            background: "linear-gradient(180deg, #1d1a17 0%, #141210 100%)",
            border: "2px solid #3a332c",
            boxShadow: "0 0 120px 20px rgba(255, 214, 160, 0.18)",
          }}
        >
          <div style={{ fontSize: 112, fontWeight: 800, letterSpacing: 10, color: "#f4ead8" }}>CINESENSE</div>
          <div style={{ fontSize: 40, color: "#e8c98f", marginTop: 18 }}>Don&apos;t choose a movie.</div>
          <div style={{ fontSize: 40, color: "#e8c98f" }}>Choose a feeling.</div>
          <div style={{ fontSize: 24, color: "#a99d8c", marginTop: 26 }}>Films by mood · streaming and cinema in Germany</div>
        </div>
      </div>
    ),
    size,
  );
}
