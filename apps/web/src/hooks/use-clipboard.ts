"use client";
import { useCallback, useState } from "react";

export function useClipboard(timeout = 2000) {
  const [copiedId, setCopiedId] = useState<string | null>(null);
  const copy = useCallback(async (id: string, text: string) => {
    try {
      if (navigator.clipboard?.writeText) {
        await navigator.clipboard.writeText(text);
      } else {
        const textarea = document.createElement("textarea");
        textarea.value = text;
        textarea.setAttribute("readonly", "true");
        textarea.style.position = "fixed";
        textarea.style.opacity = "0";
        document.body.appendChild(textarea);
        textarea.select();
        const copied = document.execCommand("copy");
        document.body.removeChild(textarea);
        if (!copied) throw new Error("浏览器拒绝了复制操作");
      }
      setCopiedId(id);
      setTimeout(() => setCopiedId(null), timeout);
    } catch {
      // Copy is a convenience action; keep the hook non-throwing for callers.
      setCopiedId(null);
    }
  }, [timeout]);
  return { copiedId, copy };
}
