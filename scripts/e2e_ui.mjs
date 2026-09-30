#!/usr/bin/env node
/**
 * Real-browser acceptance run for the Mago workbench.
 *
 * It drives the actual UI with the system Chrome (playwright-core, no browser
 * download) and proves the thing unit tests cannot: a creator can click from an
 * empty text box to a prompt they have physically on their clipboard.
 *
 * Usage:
 *   make e2e                                   # needs web :3000 + agent :8000
 *   node scripts/e2e_ui.mjs --base http://localhost:3000 --headed
 *   node scripts/e2e_ui.mjs --demo             # demo mode (no backend at all)
 *   node scripts/e2e_ui.mjs --live             # real registration, project, and backend
 *
 * Exit codes: 0 passed, 1 assertion failed, 2 environment problem.
 */
import { mkdirSync, writeFileSync } from "node:fs";
import { execSync } from "node:child_process";
import { createRequire } from "node:module";

// playwright-core lives in apps/web (it is a devDependency of the web app).
// Resolving from there keeps this script runnable from the repo root while
// still letting CI install only the workspace it needs.
const requireFromWeb = createRequire(new URL("../apps/web/package.json", import.meta.url));
let chromium;
try {
  ({ chromium } = requireFromWeb("playwright-core"));
} catch {
  console.log("\x1b[31m缺少 playwright-core。安装：./scripts/pnpm.sh --dir apps/web add -D playwright-core\x1b[0m");
  process.exit(2);
}

const argv = process.argv.slice(2);
function flag(name, fallback = "") {
  const i = argv.indexOf(`--${name}`);
  return i >= 0 && argv[i + 1] && !argv[i + 1].startsWith("--") ? argv[i + 1] : fallback;
}
const has = (name) => argv.includes(`--${name}`);

// The studio keeps the chat pane mounted (display:none) while the 脚本/分镜 tabs
// are active, so *every* locator in this script must be visibility-filtered:
// `.first()` alone happily matches the hidden duplicate and then waits forever.
const visAll = (loc) => loc.locator("visible=true");
const vis = (loc) => visAll(loc).first();

const base = (flag("base", "http://localhost:3000")).replace(/\/$/, "");
const outDir = flag("shots", "/tmp/mago-e2e");
const demo = has("demo");
const live = has("live");
const topic = flag("topic", "口红测评，第一视角，30秒");
let projectId = flag("project", demo ? "e2e-demo-run" : "");

const results = [];
function check(cond, label, detail = "") {
  results.push({ ok: !!cond, label, detail });
  const mark = cond ? "\x1b[32m✓\x1b[0m" : "\x1b[31m✗\x1b[0m";
  console.log(`  ${mark} ${label}${cond ? "" : "\n      → " + detail}`);
}

function chromeExecutable() {
  if (process.env.CHROME_PATH) return process.env.CHROME_PATH;
  const candidates = [
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/Applications/Chromium.app/Contents/MacOS/Chromium",
    "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
  ];
  for (const path of candidates) {
    try {
      execSync(`test -x "${path}"`, { stdio: "ignore" });
      return path;
    } catch {
      /* try next */
    }
  }
  try {
    return execSync("command -v google-chrome chromium chromium-browser 2>/dev/null | head -1", { encoding: "utf8" }).trim() || null;
  } catch {
    return null;
  }
}

async function shot(page, name) {
  const file = `${outDir}/${name}.png`;
  await page.screenshot({ path: file, fullPage: false }).catch(() => {});
  // Screenshots are not always viewable headless/CI, so keep the text too.
  await page
    .locator("body")
    .innerText()
    .then((text) => writeFileSync(`${outDir}/${name}.txt`, text))
    .catch(() => {});
  console.log(`      \x1b[2m截图/文本 ${outDir}/${name}.{png,txt}\x1b[0m`);
}

function summary() {
  const failed = results.filter((r) => !r.ok);
  console.log("");
  if (failed.length) {
    console.log(`\x1b[31m✗ 浏览器验收未通过：${failed.length} 项失败（共 ${results.length} 项）\x1b[0m`);
    return 1;
  }
  console.log(`\x1b[32m✓ 浏览器验收全部通过：${results.length} 项\x1b[0m`);
  return 0;
}

async function main() {
  if (demo && live) {
    console.log("\x1b[31m--demo 与 --live 不能同时使用。\x1b[0m");
    return 2;
  }
  mkdirSync(outDir, { recursive: true });
  const exe = chromeExecutable();
  if (!exe) {
    console.log("\x1b[31m找不到 Chrome/Chromium。安装任一浏览器，或设置 CHROME_PATH 后重试。\x1b[0m");
    return 2;
  }
  const browser = await chromium.launch({
    executablePath: exe,
    headless: !has("headed"),
    // A system Chrome may load enterprise or user extensions even when
    // Playwright creates a temporary profile. Keep the acceptance run clean
    // and deterministic (extensions can mutate DOM before React hydrates).
    args: ["--no-sandbox", "--disable-dev-shm-usage", "--disable-extensions"],
  });
  const context = await browser.newContext({ viewport: { width: 1440, height: 900 }, deviceScaleFactor: 2 });
  await context.grantPermissions(["clipboard-read", "clipboard-write"], { origin: base });
  const page = await context.newPage();
  const consoleErrors = [];
  page.on("console", (msg) => {
    if (msg.type() === "error") consoleErrors.push(msg.text());
  });
  page.on("pageerror", (err) => consoleErrors.push(`pageerror: ${err.message}`));

  try {
    // ---------- 1. 登录并进入真实项目工作台 ----------
    console.log(`\x1b[33m[1/5] 打开工作台 ${base}\x1b[0m`);
    await page.goto(`${base}/login${live ? "?mode=register" : ""}`, { waitUntil: "domcontentloaded", timeout: 60000 });
    if (demo) {
      await page.evaluate(() => localStorage.setItem("mago_access_token", "demo_token_" + Date.now()));
    } else if (live) {
      const email = `mago-browser-e2e-${Date.now()}@example.test`;
      await page.getByPlaceholder("你的名字").fill("Mago Browser E2E");
      await page.locator('input[type="email"]').fill(email);
      await page.locator('input[type="password"]').fill("E2E-password-2026");
      // Capture the register response so a failure is diagnosable from CI logs
      // instead of surfacing only as an opaque waitForURL timeout.
      const registerResponse = page.waitForResponse(
        (response) => response.url().includes("/api/v1/auth/register"),
        { timeout: 60000 },
      );
      await page.getByRole("button", { name: "注册并进入" }).click();
      let registerStatus = 0;
      let registerBody = "";
      try {
        const response = await registerResponse;
        registerStatus = response.status();
        registerBody = await response.text().catch(() => "");
      } catch (err) {
        registerBody = "no response captured: " + (err?.message ?? err);
      }
      const navigated = await page
        .waitForURL((url) => url.pathname === "/dashboard", { timeout: 30000 })
        .then(() => true)
        .catch(() => false);
      check(
        navigated,
        "真实注册并登录成功",
        "注册接口 HTTP " + registerStatus + "；响应 " + registerBody.slice(0, 300) + "；控制台 " + consoleErrors.slice(-3).join(" | "),
      );
      if (!navigated) {
        const loginError = await page.locator("body").innerText().catch(() => "");
        console.log("      \u001b[2m登录页可见文案：" + loginError.replace(/\n+/g, " ").slice(0, 300) + "\u001b[0m");
        await shot(page, "01a-register-failed");
        throw new Error("注册未跳转 dashboard（HTTP " + registerStatus + "）");
      }

      await page.goto(`${base}/projects`, { waitUntil: "domcontentloaded", timeout: 60000 });
      await page.getByRole("button", { name: "新建项目" }).first().click();
      const projectName = `Mago browser E2E ${Date.now()}`;
      await page.getByPlaceholder("给你的项目起个名字").fill(projectName);
      await page.getByPlaceholder("简单描述这个视频项目").fill("由真实浏览器 E2E 创建");
      const createResponse = page.waitForResponse((response) =>
        response.request().method() === "POST" && response.url().endsWith("/api/v1/projects"),
        { timeout: 60000 },
      );
      await page.getByRole("button", { name: "创建", exact: true }).click();
      const response = await createResponse;
      const envelope = await response.json();
      projectId = envelope?.data?.id || "";
      check(response.ok() && !!projectId, "真实项目创建成功并取得项目 ID", `HTTP ${response.status()}`);
      if (!projectId) throw new Error("项目创建接口没有返回 data.id");
      await page.getByText(projectName, { exact: true }).waitFor({ state: "visible", timeout: 30000 });
    } else if (!projectId) {
      throw new Error("必须指定 --demo、--live 或 --project");
    }

    await page.goto(`${base}/studio/${projectId}`, { waitUntil: "domcontentloaded", timeout: 60000 });
    await page.waitForURL((url) => !url.pathname.startsWith("/login"), { timeout: 30000 }).catch(() => {});
    const studioTitle = "脚本创作中心";
    const onStudio = await vis(page.getByText(studioTitle, { exact: false })).isVisible().catch(() => false);
    check(onStudio, "工作台页面渲染成功（未被登录页挡住）", `当前地址 ${page.url()}；页面上找不到「${studioTitle}」`);
    await shot(page, "01-studio");

    // ---------- 2. 选题 → 灵感卡片 ----------
    // The studio runs mode=detailed, which deliberately stops after ideation so
    // the creator picks a direction (HITL). Assert that gate, then use it.
    console.log(`\x1b[33m[2/5] 输入选题并生成创意方向\x1b[0m`);
    const box = vis(page.getByRole("textbox"));
    await box.waitFor({ state: "visible", timeout: 30000 });
    await box.fill(topic);
    await vis(page.getByRole("button", { name: "发送消息" })).click();

    const ideaButton = vis(page.getByRole("button", { name: /用这个写脚本/ }));
    const directScript = vis(page.getByText("完整脚本", { exact: false }));
    const ideaOrScript = await Promise.race([
      ideaButton.waitFor({ state: "visible", timeout: 120000 }).then(() => "ideas"),
      directScript.waitFor({ state: "visible", timeout: 120000 }).then(() => "script"),
    ]).catch(() => "none");
    check(ideaOrScript !== "none", "选题后 SSE 产出了创意方向或脚本", "120 秒内既没有灵感卡片也没有脚本卡片，检查 Agent 是否在 :8000 运行");
    let bodyText = await page.locator("body").innerText();
    check(!/出错了[:：]/.test(bodyText), "对话区没有报错文案", (bodyText.match(/出错了[:：][^\n]{0,200}/) || [""])[0]);
    await shot(page, "02-ideas");

    // ---------- 3. 选定方向 → 脚本 + 分镜 ----------
    console.log(`\x1b[33m[3/5] 选一个方向，生成脚本与分镜\x1b[0m`);
    if (ideaOrScript === "ideas") {
      await ideaButton.scrollIntoViewIfNeeded();
      await ideaButton.click();
    }
    const gotScript = await vis(page.getByText("完整脚本", { exact: false }))
      .waitFor({ state: "visible", timeout: 120000 }).then(() => true).catch(() => false);
    check(gotScript, "脚本卡片已生成", "点「用这个写脚本」后没有出现脚本卡片");
    // The streamed storyboard callback can select its tab after the script
    // callback. Assert the script on its own tab so this check cannot pass on
    // a transient render or read the hidden panel's surrounding page text.
    await vis(page.getByRole("button", { name: "脚本", exact: true })).click();
    bodyText = await page.locator("body").innerText();
    const beats = (bodyText.match(/(\d+)\s*个节拍/) || [])[1];
    check(!!beats && Number(beats) >= 2, `脚本有节拍分解（${beats || 0} 个节拍）`, "没读到节拍数");
    const scriptBody = await vis(page.getByText("📝 正文")).locator("xpath=following-sibling::p[1]").innerText().catch(() => "");
    check(scriptBody.length > 30, "脚本正文可直接阅读（不是占位符）", `正文长度 ${scriptBody.length}`);
    await shot(page, "03-script");

    await vis(page.getByRole("button", { name: "分镜", exact: true })).click();
    const gotStoryboard = await vis(page.getByText("完整分镜表", { exact: false }))
      .waitFor({ state: "visible", timeout: 120000 }).then(() => true).catch(() => false);
    check(gotStoryboard, "分镜表已生成", "脚本之后没有出现分镜卡片");
    const shotCount = (await page.locator("body").innerText()).match(/(\d+)\s*个镜头/);
    check(!!shotCount && Number(shotCount[1]) >= 3, `分镜有 ${shotCount ? shotCount[1] : 0} 个镜头`, "镜头数不足");
    await shot(page, "04-storyboard");

    // ---------- 4. 提示词包（真正的产出物） ----------
    console.log(`\x1b[33m[4/5] 生成可复制的提示词包\x1b[0m`);
    const packTitle = vis(page.getByText("出片提示词包", { exact: false }));
    await packTitle.scrollIntoViewIfNeeded().catch(() => {});
    const packVisible = await packTitle.waitFor({ state: "visible", timeout: 30000 }).then(() => true).catch(() => false);
    check(packVisible, "分镜卡片下方出现「出片提示词包」");
    if (!packVisible) {
      await shot(page, "04-no-pack");
      return summary();
    }

    const generate = vis(page.getByRole("button", { name: /生成提示词包|重新生成/ }));
    await generate.scrollIntoViewIfNeeded();
    await generate.click();
    const promptBlock = vis(page.getByText("正向提示词", { exact: false }));
    const gotPack = await promptBlock.waitFor({ state: "visible", timeout: 60000 }).then(() => true).catch(() => false);
    check(gotPack, "提示词包渲染出正向提示词", "点击生成后没有出现提示词");

    const packText = await page.locator("body").innerText();
    const matrix = packText.match(/(\d+)\s*个镜头\s*·\s*(\d+)\s*条提示词/);
    check(!!matrix && Number(matrix[2]) > 0, `提示词条数与镜头×模型矩阵一致（${matrix ? matrix[0] : "未找到统计行"}）`, "统计行缺失说明包是空的");
    check(/参数：/.test(packText) || /duration=|seed=|aspect_ratio=/.test(packText), "每条提示词带可复制参数", "没有参数行");
    await shot(page, "05-prompt-pack");

    // ---------- 5. 真的能复制/导出 ----------
    console.log(`\x1b[33m[5/5] 复制到剪贴板（用户实际拿走的东西）\x1b[0m`);
    const copyButtons = visAll(page.getByRole("button", { name: "复制" }));
    const copyCount = await copyButtons.count();
    check(copyCount > 0, `提示词旁有 ${copyCount} 个「复制」按钮`);
    if (copyCount) {
      await copyButtons.first().scrollIntoViewIfNeeded();
      await copyButtons.first().click();
      const confirm = await vis(page.getByText("已复制")).waitFor({ state: "visible", timeout: 15000 }).then(() => true).catch(() => false);
      check(confirm, "点击复制后界面确认「已复制」");
      const clip = await page.evaluate(() => navigator.clipboard.readText().catch(() => ""));
      check(clip.length > 40, "剪贴板里确实有提示词内容", `剪贴板长度 ${clip.length}`);
      console.log(`      \x1b[2m剪贴板前 120 字：${clip.slice(0, 120).replace(/\s+/g, " ")}\x1b[0m`);
    }
    const exportButtons = visAll(page.getByRole("button", { name: /^(Markdown|纯文本|CSV|JSON|分镜表 CSV|口播 TXT)$/ }));
    const exportCount = await exportButtons.count();
    check(exportCount >= 4, `导出入口齐全（${exportCount} 种格式）`, "导出按钮不足 4 个");

    const downloads = [];
    page.on("download", (d) => downloads.push(d));
    if (exportCount >= 4) {
      await exportButtons.first().scrollIntoViewIfNeeded();
      await exportButtons.first().click().catch(() => {});
      const file = await downloads[0]?.path().catch(() => null);
      check(!!file, "Markdown 导出真的产生了文件", downloads.length ? "下载未落盘" : "没有触发下载事件");
    }

    const layoutErrors = consoleErrors.filter((line) => !/favicon|Download the React DevTools|WebSocket|websocket/i.test(line));
    check(layoutErrors.length === 0, "浏览器控制台没有应用报错", layoutErrors.slice(0, 3).join(" | "));
    await shot(page, "06-copied");

    const failed = results.filter((r) => !r.ok).length;
    console.log("");
    if (failed) {
      console.log(`\x1b[31m✗ 浏览器验收未通过：${failed} 项失败（共 ${results.length} 项）\x1b[0m`);
      return 1;
    }
    console.log(`\x1b[32m✓ 浏览器验收全部通过：${results.length} 项（截图见 ${outDir}）\x1b[0m`);
    return 0;
  } finally {
    await browser.close();
  }
}

function summary0() {
  const failed = results.filter((r) => !r.ok).length;
  console.log(`\x1b[31m✗ 浏览器验收中断：${failed} 项失败（共 ${results.length} 项）\x1b[0m`);
  return 1;
}

main().then((code) => process.exit(code)).catch((err) => {
  console.log(`\x1b[31m✗ 验收脚本异常：${err && err.stack ? err.stack : err}\x1b[0m`);
  process.exit(2);
});
