/**
 * Serialisers for generated scripts and storyboards.
 *
 * Creators paste these into teleprompter apps, spreadsheets and the downstream
 * generation tools, so the plain-text and CSV shapes are as important as the
 * JSON one and must stay stable.
 */
import type { AgentBeat, AgentScript, AgentShot, AgentStoryboard } from "./agent-output";

/** A section is either a line, a nested block, or `false` when it is absent. */
export type ExportLine = string | number | false | null | undefined | ExportLine[];

function flatten(input: ExportLine[], out: string[] = []): string[] {
  for (const item of input) {
    if (item === false || item === null || item === undefined) continue;
    if (Array.isArray(item)) {
      flatten(item, out);
      continue;
    }
    out.push(String(item));
  }
  return out;
}

/** Drop empty helper lines but keep a single blank line between sections. */
function joinLines(input: ExportLine[]): string {
  const kept: string[] = [];
  for (const text of flatten(input)) {
    if (text === "") {
      if (kept.length && kept[kept.length - 1] !== "") kept.push("");
      continue;
    }
    kept.push(text);
  }
  while (kept.length && kept[kept.length - 1] === "") kept.pop();
  return kept.join("\n") + "\n";
}

export function beatLabel(beat: AgentBeat, index: number): string {
  const phase = beat.phase || `节拍 ${index + 1}`;
  return beat.duration_sec ? `${phase} · ${beat.duration_sec}s` : phase;
}

export function scriptToMarkdown(script: AgentScript): string {
  const lines: ExportLine[] = [
    `# ${script.title || "未命名脚本"}`,
    "",
    script.target_duration_sec ? `> 目标时长 ${script.target_duration_sec} 秒${script.target_platform ? ` · ${script.target_platform}` : ""}` : "",
    "",
    script.hook ? ["## 钩子", script.hook, ""] : false,
    script.hook_variants?.length ? ["## 备选钩子", ""] : false,
    ...(script.hook_variants || []).map((variant, index) => `${index + 1}. **${variant.hook_type || `方案 ${index + 1}`}**：${variant.text || ""}`),
    script.hook_variants?.length ? [""] : false,
    script.body_text ? ["## 正文", script.body_text, ""] : false,
    script.beats?.length ? ["## 节拍分解", ""] : false,
    ...(script.beats || []).map((beat, index) =>
      `- **${beatLabel(beat, index)}** — ${beat.content || ""}${beat.visual_note ? `（画面：${beat.visual_note}）` : ""}`
    ),
    script.beats?.length ? [""] : false,
    script.cta ? ["## 行动号召 CTA", script.cta, ""] : false,
    "",
    "> 由 Mago 创意平台生成，发布前请人工复核。",
  ];
  return joinLines(lines);
}

/** No markdown at all: for teleprompter apps and plain note fields. */
export function scriptToPlainText(script: AgentScript): string {
  const lines: ExportLine[] = [
    script.title || "未命名脚本",
    "",
    script.hook ? ["【钩子】", script.hook, ""] : false,
    script.hook_variants?.length ? ["【备选钩子】", ""] : false,
    ...(script.hook_variants || []).map((variant, index) => `${index + 1}. [${variant.hook_type || `方案 ${index + 1}`}] ${variant.text || ""}`),
    script.body_text ? ["【正文】", script.body_text, ""] : false,
    script.beats?.length ? ["【节拍】", ""] : false,
    ...(script.beats || []).map((beat, index) => `${index + 1}. (${beatLabel(beat, index)}) ${beat.content || ""}`),
    script.cta ? ["【CTA】", script.cta] : false,
  ];
  return joinLines(lines);
}

export function storyboardToMarkdown(storyboard: AgentStoryboard): string {
  const lines: ExportLine[] = [
    `# ${storyboard.title || "未命名分镜"}`,
    "",
    storyboard.total_duration_sec ? `> 总时长 ${storyboard.total_duration_sec} 秒 · ${storyboard.shots?.length ?? 0} 个镜头${storyboard.aspect_ratio ? ` · ${storyboard.aspect_ratio}` : ""}` : "",
    "",
    storyboard.visual_style_notes ? [`视觉风格：${storyboard.visual_style_notes}`, ""] : false,
    ...(storyboard.shots || []).flatMap((shot, index) => [
      `## 镜头 ${shot.index ?? index + 1}（${shot.duration_sec ?? 0}s）`,
      "",
      shot.shot_size ? `- 景别：${shot.shot_size}` : "",
      shot.camera_angle ? `- 机位：${shot.camera_angle}` : "",
      shot.camera_movement ? `- 运镜：${shot.camera_movement}` : "",
      `- 画面：${shot.visual_description || ""}`,
      shot.action_description ? `- 动作：${shot.action_description}` : "",
      shot.dialogue ? `- 台词：「${shot.dialogue}」` : "",
      shot.lighting ? `- 光线：${shot.lighting}` : "",
      shot.color_tone ? `- 色调：${shot.color_tone}` : "",
      shot.transition ? `- 转场：${shot.transition}` : "",
      shot.ai_warnings?.length ? `- ⚠️ AI 风险：${shot.ai_warnings.join("；")}` : "",
      "",
    ]),
  ];
  return joinLines(lines);
}

const SHOT_COLUMNS: Array<[string, (shot: AgentShot) => string | number | undefined]> = [
  ["镜头序号", (shot) => shot.index],
  ["时长(秒)", (shot) => shot.duration_sec],
  ["景别", (shot) => shot.shot_size],
  ["机位", (shot) => shot.camera_angle],
  ["运镜", (shot) => shot.camera_movement],
  ["场景环境", (shot) => shot.scene_description || shot.scene_environment],
  ["画面描述", (shot) => shot.visual_description],
  ["动作", (shot) => shot.action_description],
  ["台词", (shot) => shot.dialogue],
  ["音效", (shot) => shot.sound_effect],
  ["光线", (shot) => shot.lighting],
  ["色调", (shot) => shot.color_tone],
  ["转场", (shot) => shot.transition],
  ["AI风险提示", (shot) => (shot.ai_warnings || []).join("；")],
];

function csvCell(value: string | number | undefined): string {
  const text = value === undefined || value === null ? "" : String(value);
  return /[",\n\r]/.test(text) ? `"${text.replace(/"/g, '""')}"` : text;
}

/** Excel/Numbers importable. Uses CRLF and a BOM-free UTF-8 body on purpose. */
export function storyboardToCsv(storyboard: AgentStoryboard): string {
  const header = SHOT_COLUMNS.map(([label]) => csvCell(label)).join(",");
  const rows = (storyboard.shots || []).map((shot, index) =>
    SHOT_COLUMNS.map(([, read], columnIndex) =>
      csvCell(columnIndex === 0 && shot.index === undefined ? index + 1 : read(shot))
    ).join(",")
  );
  return [header, ...rows].join("\r\n") + "\r\n";
}

export function scriptToJson(script: AgentScript): string {
  return JSON.stringify(script, null, 2) + "\n";
}

export function storyboardToJson(storyboard: AgentStoryboard): string {
  return JSON.stringify(storyboard, null, 2) + "\n";
}

export interface ExportOption {
  id: string;
  label: string;
  filename: string;
  mime: string;
}

export function scriptExports(script: AgentScript): ExportOption[] {
  const slug = safeSlug(script.title || "script");
  return [
    { id: "txt", label: "口播 TXT", filename: `${slug}.txt`, mime: "text/plain;charset=utf-8" },
    { id: "md", label: "Markdown", filename: `${slug}.md`, mime: "text/markdown;charset=utf-8" },
    { id: "json", label: "JSON", filename: `${slug}.json`, mime: "application/json;charset=utf-8" },
  ];
}

export function storyboardExports(storyboard: AgentStoryboard): ExportOption[] {
  const slug = safeSlug(storyboard.title || "storyboard");
  return [
    { id: "csv", label: "分镜表 CSV", filename: `${slug}.csv`, mime: "text/csv;charset=utf-8" },
    { id: "md", label: "Markdown", filename: `${slug}.md`, mime: "text/markdown;charset=utf-8" },
    { id: "json", label: "JSON", filename: `${slug}.json`, mime: "application/json;charset=utf-8" },
  ];
}

export function renderExport(kind: "script" | "storyboard", format: string, payload: AgentScript | AgentStoryboard): string {
  if (kind === "script") {
    const script = payload as AgentScript;
    if (format === "md") return scriptToMarkdown(script);
    if (format === "json") return scriptToJson(script);
    return scriptToPlainText(script);
  }
  const storyboard = payload as AgentStoryboard;
  if (format === "csv") return storyboardToCsv(storyboard);
  if (format === "json") return storyboardToJson(storyboard);
  return storyboardToMarkdown(storyboard);
}

/** File names end up on other people's machines: strip path separators. */
export function safeSlug(value: string): string {
  const cleaned = value
    .replace(/[\\/:*?"<>|\u0000-\u001f]/g, "")
    .replace(/\s+/g, "-")
    .replace(/-+/g, "-")
    .slice(0, 60)
    .replace(/^-|-$/g, "");
  return cleaned || "mago-export";
}

/** Prepend a BOM so Excel opens Chinese CSV files without mojibake. */
export function downloadText(filename: string, text: string, mime: string): void {
  const body = mime.startsWith("text/csv") ? `\uFEFF${text}` : text;
  const blob = new Blob([body], { type: mime });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  anchor.rel = "noopener";
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  // Revoke on the next tick so Safari has time to start the download.
  window.setTimeout(() => URL.revokeObjectURL(url), 1000);
}

export async function copyToClipboard(text: string): Promise<boolean> {
  try {
    if (navigator.clipboard?.writeText) {
      await navigator.clipboard.writeText(text);
      return true;
    }
  } catch {
    // fall through to the legacy path (insecure contexts block the async API)
  }
  try {
    const area = document.createElement("textarea");
    area.value = text;
    area.setAttribute("readonly", "");
    area.style.position = "fixed";
    area.style.opacity = "0";
    document.body.appendChild(area);
    area.focus();
    area.select();
    const ok = document.execCommand("copy");
    area.remove();
    return ok;
  } catch {
    return false;
  }
}
