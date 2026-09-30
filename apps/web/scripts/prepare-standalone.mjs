import { cp, mkdir } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

const appDir = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const nextDir = path.join(appDir, ".next");
const standaloneAppDir = path.join(nextDir, "standalone", "apps", "web");

await mkdir(path.join(standaloneAppDir, ".next"), { recursive: true });
await cp(path.join(nextDir, "static"), path.join(standaloneAppDir, ".next", "static"), { recursive: true, force: true });
await cp(path.join(appDir, "public"), path.join(standaloneAppDir, "public"), { recursive: true, force: true });
console.log("Prepared Next.js standalone assets.");
