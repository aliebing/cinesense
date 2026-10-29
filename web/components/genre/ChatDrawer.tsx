"use client";

import { useState } from "react";
import ChatPanel from "@/components/chat/ChatPanel";

/** Collapsible glass chat at the right edge of the genre page; same conversation in Plan 3. */
export default function ChatDrawer() {
  const [open, setOpen] = useState(false);
  if (!open) {
    return (
      <button type="button" className="drawer-tab" aria-expanded="false" onClick={() => setOpen(true)}>
        💬 Chat
      </button>
    );
  }
  return (
    <aside className="drawer" aria-label="Chat">
      <header className="drawer-head">
        <span>Weiter eingrenzen</span>
        <button type="button" aria-label="Chat schließen" onClick={() => setOpen(false)}>
          ×
        </button>
      </header>
      <ChatPanel mode="static" />
    </aside>
  );
}
