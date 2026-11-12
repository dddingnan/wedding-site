import { useSyncExternalStore } from "react";

// Admin JWT kept in sessionStorage (cleared when the tab closes).
// Exposed as an external store so React reads it without a hydration mismatch:
// the server snapshot is always null, the client reads the real value.

const KEY = "wedding-admin-token";
const listeners = new Set<() => void>();

function read(): string | null {
  try {
    return sessionStorage.getItem(KEY);
  } catch {
    return null; // private mode / storage blocked
  }
}

export function setAdminToken(token: string | null) {
  try {
    if (token) sessionStorage.setItem(KEY, token);
    else sessionStorage.removeItem(KEY);
  } catch {
    /* storage blocked: the token just won't survive a reload */
  }
  listeners.forEach((l) => l());
}

function subscribe(listener: () => void) {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

export function useAdminToken() {
  return useSyncExternalStore(subscribe, read, () => null);
}
