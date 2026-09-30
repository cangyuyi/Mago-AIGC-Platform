import { afterEach } from "vitest";
import { cleanup } from "@testing-library/react";
import "@testing-library/jest-dom/vitest";

afterEach(() => cleanup());

// jsdom does not always expose WebCrypto; saveGeneration needs it for ids.
if (typeof globalThis.crypto?.randomUUID !== "function") {
  const shim = { randomUUID: () => "11111111-1111-4111-8111-111111111111" };
  Object.defineProperty(globalThis, "crypto", { value: shim, configurable: true });
}
