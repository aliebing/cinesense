"use client";

import { useSyncExternalStore } from "react";

// App-wide: only one hover trailer plays at a time.
let activeId: string | null = null;
const listeners = new Set<() => void>();

function emit() {
  listeners.forEach((l) => l());
}

export function resetActiveTrailer() {
  activeId = null;
  emit();
}

function activate(next: string) {
  activeId = next;
  emit();
}

function deactivate(current: string) {
  if (activeId === current) {
    activeId = null;
    emit();
  }
}

export function useActiveTrailer() {
  const id = useSyncExternalStore(
    (cb) => {
      listeners.add(cb);
      return () => listeners.delete(cb);
    },
    () => activeId,
    () => null,
  );
  return { activeId: id, activate, deactivate };
}
