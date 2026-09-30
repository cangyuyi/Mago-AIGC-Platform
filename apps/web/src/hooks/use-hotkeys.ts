"use client";
import { useEffect } from "react";

export function useHotkeys(keys: Record<string, () => void>) {
  useEffect(() => {
    function handler(e: KeyboardEvent) {
      const key = (e.metaKey ? "cmd+" : e.ctrlKey ? "ctrl+" : "") + e.key.toLowerCase();
      if (keys[key]) {
        e.preventDefault();
        keys[key]();
      }
    }
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [keys]);
}
