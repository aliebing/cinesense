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

/** Silences a player at once: Next keeps visited pages alive but hidden (cacheComponents), and a hidden iframe
 *  would go on playing. Called from effect cleanups, which run when a page is hidden or left. */
export function silence(frame: RefObject<HTMLIFrameElement | null>) {
  if (frame.current) frame.current.src = "about:blank";
}

/** Ask the embedded player to post its state and errors to this page. */
export function listenTo(frame: RefObject<HTMLIFrameElement | null>, id: string) {
  frame.current?.contentWindow?.postMessage(JSON.stringify({ event: "listening", id, channel: "widget" }), YT_ORIGIN);
}

const BLOCKED = new Set([100, 101, 150]); // not found / embedding not allowed (incl. region blocks)
const HANDSHAKE_MS = 250;
const HANDSHAKE_GIVE_UP_MS = 5000;
const SHOW_ANYWAY_MS = 2500;

/** Follows an embedded YouTube player: `playing` once it plays (or after 2.5 s without news, so a missed
 *  handshake never hides a trailer), `failed` when it reports an error. Only "blocked/not found" errors are
 *  reported to the backend; other errors just fall back to the image in this tile. */
export function useYouTubeState(
  active: boolean,
  key: string | null,
  frame?: RefObject<HTMLIFrameElement | null>,
  id?: string,
): { playing: boolean; failed: boolean } {
  const [state, setState] = useState<{ key: string | null; playing: boolean; failed: boolean }>({
    key,
    playing: false,
    failed: false,
  });
  useEffect(() => {
    if (!active || !key) return;
    let heard = false;
    let settled = false;
    const started = Date.now();
    const handshake = setInterval(() => {
      if (heard || Date.now() - started > HANDSHAKE_GIVE_UP_MS) return clearInterval(handshake);
      if (frame && id) listenTo(frame, id); // the player may not be ready at onLoad: keep asking
    }, HANDSHAKE_MS);
    const showAnyway = setTimeout(() => {
      if (!settled) setState((s) => (s.key === key && s.failed ? s : { key, playing: true, failed: false }));
    }, SHOW_ANYWAY_MS);
    const onMessage = (e: MessageEvent) => {
      if (e.origin !== YT_ORIGIN) return;
      const own = frame?.current?.contentWindow;
      if (e.source && own && e.source !== own) return; // another player's late message
      const msg = parse(e.data);
      if (!msg) return;
      heard = true;
      const info = msg.info;
      const playerState = typeof info === "object" ? info?.playerState : msg.event === "onStateChange" ? info : undefined;
      if (playerState === 1) {
        settled = true;
        setState({ key, playing: true, failed: false });
      }
      if (msg.event === "onError") {
        settled = true;
        setState({ key, playing: false, failed: true });
        if (typeof info === "number" && BLOCKED.has(info)) {
          badKeys.add(key);
          void reportTrailer(key);
        }
      }
    };
    window.addEventListener("message", onMessage);
    return () => {
      clearInterval(handshake);
      clearTimeout(showAnyway);
      window.removeEventListener("message", onMessage);
    };
  }, [active, key, frame, id]);
  const current = state.key === key ? state : { playing: false, failed: false };
  return { playing: active && current.playing && !current.failed, failed: current.failed || isBadTrailer(key) };
}
