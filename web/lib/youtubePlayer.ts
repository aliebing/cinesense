"use client";

import { type RefObject, useEffect, useState } from "react";
import { reportTrailer } from "@/lib/api";

export const YT_ORIGIN = "https://www.youtube-nocookie.com";
/** Trailers the player could not play in this session (deleted, blocked in Germany, embedding off). */
const badKeys = new Set<string>();

type PlayerMessage = { event?: string; info?: number | { playerState?: number } };

function parse(data: unknown): PlayerMessage | null {
  try {
    return typeof data === "string" ? (JSON.parse(data) as PlayerMessage) : null;
  } catch {
    return null;
  }
}

export function isBadTrailer(key: string | null | undefined): boolean {
  return !!key && badKeys.has(key);
}

export function embedUrl(key: string, params: string): string {
  return `${YT_ORIGIN}/embed/${encodeURIComponent(key)}?${params}&enablejsapi=1`;
}

/** Ask the embedded player to post its state and errors to this page. */
export function listenTo(frame: RefObject<HTMLIFrameElement | null>, id: string) {
  frame.current?.contentWindow?.postMessage(JSON.stringify({ event: "listening", id, channel: "widget" }), YT_ORIGIN);
}

/** Follows an embedded YouTube player: `playing` once it really plays, `failed` when it reports an error
 *  (the id is then reported to the backend and never offered again in this session). */
export function useYouTubeState(active: boolean, key: string | null): { playing: boolean; failed: boolean } {
  const [state, setState] = useState<{ key: string | null; playing: boolean; failed: boolean }>({
    key,
    playing: false,
    failed: false,
  });
  useEffect(() => {
    if (!active || !key) return;
    const onMessage = (e: MessageEvent) => {
      if (e.origin !== YT_ORIGIN) return;
      const msg = parse(e.data);
      if (!msg) return;
      const info = msg.info;
      const playerState = typeof info === "object" ? info?.playerState : msg.event === "onStateChange" ? info : undefined;
      if (playerState === 1) setState({ key, playing: true, failed: false });
      if (msg.event === "onError") {
        badKeys.add(key);
        setState({ key, playing: false, failed: true });
        void reportTrailer(key);
      }
    };
    window.addEventListener("message", onMessage);
    return () => window.removeEventListener("message", onMessage);
  }, [active, key]);
  const current = state.key === key ? state : { playing: false, failed: false };
  return { playing: active && current.playing, failed: current.failed || isBadTrailer(key) };
}
