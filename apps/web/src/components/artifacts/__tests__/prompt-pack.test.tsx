import { beforeEach, describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { PromptPackPanel } from "@/components/artifacts/prompt-pack";
import { GeneratedStoryboardOutput } from "@/components/artifacts/output-cards";
import type { AgentStoryboard } from "@/lib/agent-output";

const storyboard: AgentStoryboard = {
  id: "sb1",
  title: "口红测评分镜",
  aspect_ratio: "9:16",
  shots: [{ index: 1, duration_sec: 3, shot_size: "特写", visual_description: "口红旋出", lighting: "natural" }],
};

const packageBody = {
  package: {
    id: "pk1",
    storyboard_id: "sb1",
    name: "口红测评提示词包",
    total_shots: 1,
    selected_models: ["kling-v3"],
    aspect_ratio: "9:16",
    prompts: [
      {
        model_id: "kling-v3",
        model_name: "可灵 2.1 Master",
        prompt_type: "video",
        positive_prompt: "口红旋出；镜头：特写(CU)；光线：自然光",
        negative_prompt: "模糊，变形手",
        parameters: { duration: 3, fps: 24, seed: 12345 },
        language: "zh",
        warnings: ["duration 已按镜头时长 3s 取整"],
        quality_notes: "",
        shot_index: 1,
        package_id: "pk1",
      },
    ],
  },
  generated_by: "prompt_engine_template",
  available_models: ["kling-v3"],
  llm_configured: false,
};

function reply(body: unknown): Response {
  return { ok: true, status: 200, json: async () => body, text: async () => JSON.stringify(body) } as unknown as Response;
}

beforeEach(() => {
  Object.defineProperty(window.URL, "createObjectURL", { value: vi.fn(() => "blob:mock"), configurable: true });
  Object.defineProperty(window.URL, "revokeObjectURL", { value: vi.fn(), configurable: true });
});

function stubFetch(calls: string[]) {
  return vi.fn(async (url: string, init?: RequestInit) => {
    calls.push(String(url));
    if (String(url).endsWith("prompt-models")) {
      return reply({ models: [
        { model_id: "kling-v3", display_name: "可灵 2.1 Master", vendor: "Kuaishou", prompt_type: "video", supports_negative: true, aspect_ratios: [] },
        { model_id: "midjourney-v7", display_name: "Midjourney V7", vendor: "Midjourney", prompt_type: "image", supports_negative: false, aspect_ratios: [] },
      ] });
    }
    void init;
    return reply(packageBody);
  });
}

describe("PromptPackPanel", () => {
  it("lists models and generates a pack on demand", async () => {
    const calls: string[] = [];
    vi.stubGlobal("fetch", stubFetch(calls));
    render(<PromptPackPanel storyboard={storyboard} projectId="p1" />);

    expect(await screen.findByText("可灵 2.1 Master")).toBeInTheDocument();
    // the language chip is part of the button name, so state it in words for AT
    expect(await screen.findByText(/可直接用中文提示词/)).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: /生成提示词包/ }));

    expect(await screen.findByText("口红旋出；镜头：特写(CU)；光线：自然光")).toBeInTheDocument();
    expect(screen.getByText("模糊，变形手")).toBeInTheDocument();
    expect(screen.getByText(/seed=12345/)).toBeInTheDocument();
    expect(screen.getByText(/duration 已按镜头时长/)).toBeInTheDocument();
    expect(calls).toContain("/api/agent/prompt-pack");
  });

  it("says the output is engine-templated, not model-written", async () => {
    vi.stubGlobal("fetch", stubFetch([]));
    render(<PromptPackPanel storyboard={storyboard} />);
    expect(screen.getByText(/不消耗模型额度/)).toBeInTheDocument();
  });

  it("blocks generation when no model is selected", async () => {
    vi.stubGlobal("fetch", stubFetch([]));
    render(<PromptPackPanel storyboard={storyboard} />);
    fireEvent.click(await screen.findByRole("button", { name: /Midjourney V7/ }));
    fireEvent.click(screen.getByRole("button", { name: /可灵 2\.1 Master/ }));
    expect(screen.getByRole("button", { name: /生成提示词包/ })).toBeDisabled();
    expect(screen.getByText("至少选择一个模型")).toBeInTheDocument();
  });

  it("shows the server reason when generation is rejected", async () => {
    vi.stubGlobal("fetch", vi.fn(async (url: string) => {
      if (String(url).endsWith("prompt-models")) return reply({ models: [] });
      return { ok: false, status: 422, text: async () => JSON.stringify({ detail: "第 1 号镜头缺少画面描述" }) } as unknown as Response;
    }));
    render(<PromptPackPanel storyboard={storyboard} />);
    await waitFor(() => expect(screen.queryByText("模型清单加载中…")).not.toBeInTheDocument());
    fireEvent.click(screen.getByRole("button", { name: /生成提示词包/ }));
    expect(await screen.findByText("第 1 号镜头缺少画面描述")).toBeInTheDocument();
  });

  it("refuses without a storyboard", () => {
    vi.stubGlobal("fetch", stubFetch([]));
    render(<PromptPackPanel storyboard={{ shots: [] }} />);
    expect(screen.getByText("还没有分镜表，请先生成分镜表")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /生成提示词包/ })).toBeDisabled();
  });

  it("is reachable from the storyboard card, which is where creators look", async () => {
    vi.stubGlobal("fetch", stubFetch([]));
    render(<GeneratedStoryboardOutput storyboard={storyboard} projectId="p1" />);
    expect(screen.getByText("出片提示词包")).toBeInTheDocument();
  });
});
