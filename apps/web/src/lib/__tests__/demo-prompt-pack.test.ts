import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { fetchWithAuth } from "@/lib/auth";

/**
 * Demo mode ships no backend, so the prompt-engine endpoints must be answered
 * locally. Before this guard existed the request fell through to the Next.js
 * rewrite and returned HTTP 500, which made the whole demo creator journey
 * fail — the exact regression these tests lock down.
 */
describe("fetchWithAuth in demo mode", () => {
  beforeEach(() => {
    window.localStorage.clear();
    window.localStorage.setItem("mago_access_token", "demo_token_123");
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    window.localStorage.clear();
  });

  it("answers /api/agent/prompt-models locally without touching the network", async () => {
    const fetchMock = vi.fn();
    vi.stubGlobal("fetch", fetchMock);

    const response = await fetchWithAuth("/api/agent/prompt-models");

    expect(fetchMock).not.toHaveBeenCalled();
    expect(response.status).toBe(200);
    const body = (await response.json()) as { models: Array<{ model_id: string }> };
    expect(body.models.length).toBeGreaterThanOrEqual(3);
    expect(body.models.map((m) => m.model_id)).toContain("kling-v3");
  });

  it("answers /api/agent/prompt-pack locally with one prompt per shot × model", async () => {
    const fetchMock = vi.fn();
    vi.stubGlobal("fetch", fetchMock);

    const response = await fetchWithAuth("/api/agent/prompt-pack", {
      method: "POST",
      body: JSON.stringify({
        storyboard: {
          id: "sb-demo",
          aspect_ratio: "9:16",
          shots: [
            { index: 1, visual_description: "口红旋出特写", shot_size: "特写" },
            { index: 2, visual_description: "涂在嘴唇上", shot_size: "近景" },
          ],
        },
        target_models: ["kling-v3", "midjourney-v7"],
      }),
    });

    expect(fetchMock).not.toHaveBeenCalled();
    expect(response.status).toBe(200);
    const body = (await response.json()) as {
      package: { total_shots: number; selected_models: string[]; prompts: Array<Record<string, unknown>> };
      generated_by: string;
      llm_configured: boolean;
    };
    expect(body.package.total_shots).toBe(2);
    expect(body.package.selected_models).toEqual(["kling-v3", "midjourney-v7"]);
    expect(body.package.prompts).toHaveLength(4); // 2 shots × 2 models
    expect(body.generated_by).toBe("prompt_engine_template");
    expect(body.llm_configured).toBe(false);

    const first = body.package.prompts[0];
    expect(String(first.positive_prompt)).toContain("口红旋出特写");
    expect((first.parameters as Record<string, unknown>).seed).toBeTypeOf("number");
    expect(first.shot_index).toBe(1);
  });

  it("returns 422 for an empty storyboard instead of 500", async () => {
    const response = await fetchWithAuth("/api/agent/prompt-pack", {
      method: "POST",
      body: JSON.stringify({ storyboard: { shots: [] }, target_models: [] }),
    });
    expect(response.status).toBe(422);
  });

  it("still short-circuits /api/agent/run with a local SSE stream", async () => {
    const fetchMock = vi.fn();
    vi.stubGlobal("fetch", fetchMock);
    const response = await fetchWithAuth("/api/agent/run", {
      method: "POST",
      body: JSON.stringify({ message: "口红测评", mode: "detailed" }),
    });
    expect(fetchMock).not.toHaveBeenCalled();
    expect(response.status).toBe(200);
    expect(response.headers.get("content-type")).toContain("text/event-stream");
  });
});
