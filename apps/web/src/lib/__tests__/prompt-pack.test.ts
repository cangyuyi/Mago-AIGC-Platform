import { describe, expect, it, vi, beforeEach } from "vitest";
import {
  defaultModelSelection,
  formatParameters,
  groupShotIndexes,
  listPromptModels,
  modelLanguage,
  packageToCsv,
  packageToJson,
  packageToMarkdown,
  packageToPlainText,
  promptPackExports,
  requestPromptPack,
  type PromptItem,
  type PromptModel,
  type PromptPackage,
} from "@/lib/prompt-pack";
import type { AgentStoryboard } from "@/lib/agent-output";

const item = (over: Partial<PromptItem> = {}): PromptItem => ({
  model_id: "kling-v3",
  model_name: "可灵 2.1 Master",
  prompt_type: "video",
  positive_prompt: "口红旋出，特写，自然光",
  negative_prompt: "模糊，变形手",
  parameters: { duration: 3, fps: 24, seed: 12345 },
  language: "zh",
  aspect_ratio: "9:16",
  duration_sec: 3,
  transition: "硬切",
  warnings: ["提示词引擎模板化产出"],
  quality_notes: "Generated for 可灵",
  shot_index: 1,
  package_id: "pk1",
  ...over,
});

const pkg: PromptPackage = {
  id: "pk1",
  storyboard_id: "sb1",
  name: "口红测评提示词包",
  total_shots: 2,
  selected_models: ["kling-v3", "midjourney-v7"],
  aspect_ratio: "9:16",
  prompts: [
    item(),
    item({ model_id: "midjourney-v7", model_name: "Midjourney V7", prompt_type: "image", negative_prompt: "", shot_index: 2 }),
  ],
};

const storyboard: AgentStoryboard = {
  id: "sb1",
  aspect_ratio: "9:16",
  shots: [{ index: 1, visual_description: "口红旋出", shot_size: "特写" }],
};

function jsonResponse(body: unknown, ok = true, status = 200): Response {
  return {
    ok,
    status,
    json: async () => body,
    text: async () => JSON.stringify(body),
  } as unknown as Response;
}

beforeEach(() => {
  vi.unstubAllGlobals();
});

describe("requestPromptPack", () => {
  it("posts the storyboard and returns the package", async () => {
    const fetchMock = vi.fn(async (_url: string, _init: RequestInit) =>
      jsonResponse({ package: pkg, generated_by: "prompt_engine_template", available_models: [], llm_configured: false }),
    );
    vi.stubGlobal("fetch", fetchMock);

    const result = await requestPromptPack({ projectId: "p1", storyboard, models: ["kling-v3"] });

    expect(result.package.prompts).toHaveLength(2);
    const [url, init] = fetchMock.mock.calls[0];
    expect(url).toBe("/api/agent/prompt-pack");
    expect(JSON.parse(String(init.body)).storyboard.shots).toHaveLength(1);
  });

  it("refuses to call the network without shots", async () => {
    const fetchMock = vi.fn();
    vi.stubGlobal("fetch", fetchMock);
    await expect(requestPromptPack({ storyboard: { shots: [] } })).rejects.toThrow("先生成分镜表");
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("surfaces the server reason for a rejected pack", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => jsonResponse({ detail: "第 1 号镜头缺少画面描述" }, false, 422)));
    await expect(requestPromptPack({ storyboard })).rejects.toThrow("缺少画面描述");
  });

  it("explains how to start the agent when the service is unreachable", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => { throw new TypeError("Failed to fetch"); }));
    await expect(requestPromptPack({ storyboard })).rejects.toThrow("启动Agent服务");
  });

  it("rejects an empty prompt list instead of showing a blank panel", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => jsonResponse({ package: { ...pkg, prompts: [] } })));
    await expect(requestPromptPack({ storyboard })).rejects.toThrow("没有返回任何可用提示词");
  });
});

describe("listPromptModels", () => {
  it("falls back to the popular models when the engine is offline", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => { throw new TypeError("offline"); }));
    const models = await listPromptModels();
    expect(models.map((model) => model.model_id)).toContain("kling-v3");
  });

  it("uses the server list when available", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => jsonResponse({ models: [{ model_id: "wanx-2.1", display_name: "通义万相", vendor: "Alibaba", prompt_type: "video", supports_negative: true, aspect_ratios: [] }] })));
    expect(await listPromptModels()).toHaveLength(1);
  });

  it("keeps the language field from the server so 中文 models are not mislabelled", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => jsonResponse({ models: [{ model_id: "kling-v3", display_name: "可灵", vendor: "Kuaishou", prompt_type: "video", language: "zh", supports_negative: true, aspect_ratios: [] }] })));
    const models = await listPromptModels();
    expect(models[0]?.language).toBe("zh");
    expect(modelLanguage(models[0] as PromptModel)).toBe("zh");
  });

  it("treats a missing or unknown language as English, never as Chinese", () => {
    const base = { display_name: "x", vendor: "x", prompt_type: "image" as const, supports_negative: false, aspect_ratios: [] };
    expect(modelLanguage({ ...base, model_id: "mj" })).toBe("en");
    expect(modelLanguage({ ...base, model_id: "mj", language: "en" })).toBe("en");
    expect(modelLanguage({ ...base, model_id: "mj", language: "ja" })).toBe("en");
  });

  it("defaults to two video models plus one image model", () => {
    const models: PromptModel[] = [
      { model_id: "mj", display_name: "MJ", vendor: "x", prompt_type: "image", supports_negative: false, aspect_ratios: [] },
      { model_id: "kling", display_name: "可灵", vendor: "x", prompt_type: "video", supports_negative: true, aspect_ratios: [] },
      { model_id: "sora", display_name: "Sora", vendor: "x", prompt_type: "video", supports_negative: false, aspect_ratios: [] },
      { model_id: "flux", display_name: "Flux", vendor: "x", prompt_type: "image", supports_negative: false, aspect_ratios: [] },
    ];
    expect(defaultModelSelection(models).sort()).toEqual(["kling", "mj", "sora"]);
  });
});

describe("serialisers", () => {
  it("groups prompts by shot in stable order", () => {
    expect(groupShotIndexes([item({ shot_index: 3 }), item({ shot_index: 1 }), item({ shot_index: 3 })])).toEqual([1, 3]);
  });

  it("markdown keeps positive, negative and parameters for each model", () => {
    const md = packageToMarkdown(pkg);
    expect(md).toContain("# 口红测评提示词包");
    expect(md).toContain("## 镜头 1");
    expect(md).toContain("口红旋出，特写，自然光");
    expect(md).toContain("**负向提示词**");
    expect(md).toContain("duration=3");
  });

  it("markdown omits the negative block for models that do not support one", () => {
    const md = packageToMarkdown({ ...pkg, prompts: [item({ negative_prompt: "" })] });
    expect(md).not.toContain("**负向提示词**");
  });

  it("markdown surfaces the engine warnings so output is not mistaken for model copy", () => {
    expect(packageToMarkdown(pkg)).toContain("提示词引擎模板化产出");
  });

  it("plain text is paste-ready per shot and model", () => {
    const text = packageToPlainText(pkg);
    expect(text).toContain("镜头1 · 可灵 2.1 Master");
    expect(text).toContain("正向：口红旋出");
    expect(text.split("参数：").length - 1).toBe(2);
  });

  it("csv quotes commas inside prompts", () => {
    const csv = packageToCsv({ ...pkg, prompts: [item({ positive_prompt: "含,逗号" })] });
    expect(csv.split("\n")[0]).toContain("positive_prompt");
    expect(csv).toContain('"含,逗号"');
  });

  it("json carries a schema tag for downstream tooling", () => {
    const parsed = JSON.parse(packageToJson(pkg));
    expect(parsed.schema).toBe("mago.prompt-pack/v1");
    expect(parsed.package.prompts).toHaveLength(2);
  });

  it("formats parameters including arrays", () => {
    expect(formatParameters(item({ parameters: { fps: [24, 30] } }))).toContain("fps=24|30");
  });

  it("offers four export formats with safe file names", () => {
    const options = promptPackExports({ ...pkg, name: "口红/测评 : 合集" });
    expect(options.map((option) => option.label)).toEqual(["Markdown", "纯文本", "CSV", "JSON"]);
    for (const option of options) expect(option.filename).not.toMatch(/[\\/:*?]/);
  });
});
