/**
 * Client for the on-demand prompt-pack endpoint.
 *
 * The prompt engine turns a storyboard into per-model positive/negative
 * prompts plus the parameters each model expects. It is a deterministic
 * template layer, so it works with no LLM key and spends no model credit —
 * that is the difference between "a nice chat window" and something a creator
 * can paste into 可灵 / Midjourney / Runway today.
 */
import type { AgentScript, AgentStoryboard } from "./agent-output";
import { copyToClipboard, downloadText, safeSlug } from "./export-formats";
import { fetchWithAuth } from "./auth";

export interface PromptModel {
  model_id: string;
  display_name: string;
  vendor: string;
  prompt_type: "image" | "video";
  /** Language the model expects its own prompts in: "zh" or "en". */
  language?: string;
  supports_negative: boolean;
  aspect_ratios: string[];
}

/**
 * Which language a model wants. Trust the backend field — guessing from the
 * model id mislabels 可灵/即梦/海螺/万相 as English models, which then get an
 * untranslated Chinese prompt and silently produce garbage.
 */
export function modelLanguage(model: PromptModel): "zh" | "en" {
  return model.language === "zh" ? "zh" : "en";
}

export interface PromptItem {
  model_id: string;
  model_name: string;
  prompt_type: "image" | "video";
  positive_prompt: string;
  negative_prompt: string;
  parameters: Record<string, unknown>;
  reference_images?: Array<{ url: string; role: string; weight?: number }>;
  seed_value?: number;
  language: string;
  aspect_ratio?: string;
  duration_sec?: number | null;
  transition?: string;
  warnings?: string[];
  quality_notes: string;
  shot_index: number;
  package_id: string;
}

export interface PromptPackage {
  id: string;
  storyboard_id: string;
  name: string;
  total_shots: number;
  selected_models: string[];
  aspect_ratio?: string;
  prompts: PromptItem[];
}

export interface PromptPackResponse {
  package: PromptPackage;
  generated_by: string;
  available_models: string[];
  llm_configured: boolean;
}

const ENDPOINT = "/api/agent/prompt-pack";
const MODELS_ENDPOINT = "/api/agent/prompt-models";

async function readError(response: Response, fallback: string): Promise<string> {
  const text = await response.text();
  if (!text) return `${fallback}（HTTP ${response.status}）`;
  try {
    const data: unknown = JSON.parse(text);
    if (data && typeof data === "object") {
      const record = data as Record<string, unknown>;
      for (const key of ["detail", "message", "error"]) {
        const value = record[key];
        if (typeof value === "string" && value) return value;
      }
      const validation = record.detail;
      if (Array.isArray(validation) && validation.length) {
        return "请求参数不完整，请检查分镜数据后重试";
      }
    }
  } catch {
    // non-JSON body: fall through to the status text
  }
  return `${fallback}（HTTP ${response.status}）：${text.slice(0, 200)}`;
}

/** Ask the backend engine for prompts. Throws with a creator-readable reason. */
export async function requestPromptPack(input: {
  projectId?: string | null;
  storyboard: AgentStoryboard;
  script?: AgentScript | null;
  characters?: Array<Record<string, unknown>>;
  style?: Record<string, unknown> | null;
  models?: string[];
}): Promise<PromptPackResponse> {
  const shots = input.storyboard.shots || [];
  if (!shots.length) throw new Error("还没有分镜表，请先生成分镜表再导出提示词");

  let response: Response;
  try {
    response = await fetchWithAuth(ENDPOINT, {
      method: "POST",
      body: JSON.stringify({
        storyboard: input.storyboard,
        script: input.script ?? null,
        characters: input.characters ?? [],
        style: input.style ?? null,
        target_models: input.models ?? [],
        project_id: input.projectId ?? null,
      }),
    });
  } catch (cause) {
    // A refused proxy request means the Python service is not running, which
    // reads nothing like the HTTP error the browser actually logged.
    throw new Error(
      "无法连接提示词引擎服务（Agent 服务）。请先启动它：双击「启动Agent服务.command」，或在项目根目录执行 make agent。",
      { cause },
    );
  }
  if (!response.ok) throw new Error(await readError(response, "提示词包生成失败"));

  const data = (await response.json()) as PromptPackResponse;
  if (!data?.package?.prompts?.length) throw new Error("提示词引擎没有返回任何可用提示词，请补全分镜的画面描述后重试");
  return data;
}

/** Used only when the Agent service is unreachable, so the picker is never empty. */
const FALLBACK_MODELS: PromptModel[] = [
  { model_id: "kling-v3", display_name: "可灵 2.1 Master", vendor: "Kuaishou", prompt_type: "video", language: "zh", supports_negative: true, aspect_ratios: [] },
  { model_id: "midjourney-v7", display_name: "Midjourney V7", vendor: "Midjourney", prompt_type: "image", language: "en", supports_negative: false, aspect_ratios: [] },
  { model_id: "sora-turbo", display_name: "Sora Turbo", vendor: "OpenAI", prompt_type: "video", language: "en", supports_negative: false, aspect_ratios: [] },
];

/** Model list for the picker; degrades to the three most-used models offline. */
export async function listPromptModels(): Promise<PromptModel[]> {
  try {
    const response = await fetchWithAuth(MODELS_ENDPOINT);
    if (!response.ok) return FALLBACK_MODELS;
    const data = (await response.json()) as { models?: PromptModel[] };
    return data.models?.length ? data.models : FALLBACK_MODELS;
  } catch {
    return FALLBACK_MODELS;
  }
}

export function defaultModelSelection(models: PromptModel[]): string[] {
  const video = models.filter((model) => model.prompt_type === "video").slice(0, 2);
  const image = models.filter((model) => model.prompt_type === "image").slice(0, 1);
  const picked = [...video, ...image];
  return (picked.length ? picked : models.slice(0, 3)).map((model) => model.model_id);
}

function line(value: string): string {
  return value;
}

/** Markdown grouped by shot: one block per shot, one fenced prompt per model. */
export function packageToMarkdown(pkg: PromptPackage): string {
  const out: string[] = [
    `# ${pkg.name || "提示词包"}`,
    "",
    `> 由 Mago 提示词引擎按各模型规则模板化生成（不消耗模型额度）。参数中的 seed 已按镜头锁定，便于同一镜头多模型对比。`,
    "",
    `- 分镜编号：${pkg.storyboard_id || "—"}`,
    `- 镜头数：${pkg.total_shots}`,
    `- 画面比例：${pkg.aspect_ratio || "—"}`,
    `- 目标模型：${pkg.selected_models.join("、")}`,
    "",
  ];
  for (const shotIndex of groupShotIndexes(pkg.prompts)) {
    const items = pkg.prompts.filter((prompt) => prompt.shot_index === shotIndex);
    out.push(line(`## 镜头 ${shotIndex}`), "");
    for (const item of items) {
      out.push(
        `### ${item.model_name}（${item.prompt_type === "video" ? "视频" : "图像"}）`,
        "",
        "**正向提示词**",
        "",
        "```text",
        item.positive_prompt,
        "```",
        "",
      );
      if (item.negative_prompt) {
        out.push("**负向提示词**", "", "```text", item.negative_prompt, "```", "");
      }
      out.push(
        `参数：${formatParameters(item)}`,
        "",
      );
      for (const warning of item.warnings || []) out.push(`⚠️ ${warning}`, "");
    }
  }
  return out.join("\n");
}

/** Plain text for people pasting straight into a generation UI. */
export function packageToPlainText(pkg: PromptPackage): string {
  const out: string[] = [`${pkg.name || "提示词包"}（${pkg.total_shots} 个镜头 / ${pkg.selected_models.length} 个模型）`, ""];
  for (const item of pkg.prompts) {
    out.push(
      `镜头${item.shot_index} · ${item.model_name}`,
      `正向：${item.positive_prompt}`,
      ...(item.negative_prompt ? [`负向：${item.negative_prompt}`] : []),
      `参数：${formatParameters(item)}`,
      "",
    );
  }
  return out.join("\n");
}

export function packageToJson(pkg: PromptPackage): string {
  return JSON.stringify(
    {
      schema: "mago.prompt-pack/v1",
      generated_by: "prompt_engine_template",
      exported_at: new Date().toISOString(),
      package: pkg,
    },
    null,
    2,
  );
}

export function packageToCsv(pkg: PromptPackage): string {
  const header = ["shot_index", "model_id", "model_name", "prompt_type", "positive_prompt", "negative_prompt", "parameters", "warnings"];
  const escape = (value: string) => `"${value.replace(/"/g, '""')}"`;
  const rows = pkg.prompts.map((item) =>
    [
      String(item.shot_index),
      item.model_id,
      item.model_name,
      item.prompt_type,
      item.positive_prompt,
      item.negative_prompt,
      JSON.stringify(item.parameters),
      (item.warnings || []).join("；"),
    ].map(escape).join(","),
  );
  return [header.join(","), ...rows].join("\n");
}

export function groupShotIndexes(prompts: PromptItem[]): number[] {
  const seen: number[] = [];
  for (const item of prompts) {
    if (!seen.includes(item.shot_index)) seen.push(item.shot_index);
  }
  return seen.sort((left, right) => left - right);
}

export function formatParameters(item: PromptItem): string {
  return Object.entries(item.parameters)
    .map(([key, value]) => `${key}=${Array.isArray(value) ? value.join("|") : String(value)}`)
    .join(" · ");
}

export interface PromptExportOption {
  label: string;
  filename: string;
  mime: string;
  render: (pkg: PromptPackage) => string;
}

export function promptPackExports(pkg: PromptPackage): PromptExportOption[] {
  const slug = safeSlug(pkg.name || "prompt-pack");
  return [
    { label: "Markdown", filename: `${slug}-提示词包.md`, mime: "text/markdown", render: packageToMarkdown },
    { label: "纯文本", filename: `${slug}-提示词包.txt`, mime: "text/plain", render: packageToPlainText },
    { label: "CSV", filename: `${slug}-提示词包.csv`, mime: "text/csv", render: packageToCsv },
    { label: "JSON", filename: `${slug}-提示词包.json`, mime: "application/json", render: packageToJson },
  ];
}

export function downloadPromptPack(pkg: PromptPackage, option: PromptExportOption): void {
  downloadText(option.filename, option.render(pkg), option.mime);
}

export { copyToClipboard };
