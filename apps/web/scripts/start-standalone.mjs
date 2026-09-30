import { spawn } from "node:child_process";
import path from "node:path";
import { fileURLToPath } from "node:url";

const appDir = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const server = path.join(appDir, ".next", "standalone", "apps", "web", "server.js");
const args = process.argv.slice(2);

for (let i = 0; i < args.length; i += 1) {
  if ((args[i] === "-p" || args[i] === "--port") && args[i + 1]) {
    process.env.PORT = args[i + 1];
    i += 1;
  } else if ((args[i] === "-H" || args[i] === "--hostname") && args[i + 1]) {
    process.env.HOSTNAME = args[i + 1];
    i += 1;
  }
}

const child = spawn(process.execPath, [server], {
  cwd: appDir,
  env: process.env,
  stdio: "inherit",
});

child.on("exit", (code, signal) => {
  if (signal) process.kill(process.pid, signal);
  process.exit(code ?? 1);
});
