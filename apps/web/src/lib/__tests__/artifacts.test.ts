import { beforeEach, describe, expect, it, vi } from "vitest";
import type { AgentScript, AgentStoryboard } from "@/lib/agent-output";

const auth = vi.hoisted(() => ({ isDemoMode: vi.fn(() => false), apiFetch: vi.fn() }));
vi.mock("@/lib/auth", () => auth);

import {
  deleteGeneration,
  isUuid,
  listGenerations,
  mergeGenerations,
  resolveStorage,
  saveGeneration,
  toShotRows,
  type SavedGeneration,
} from "@/lib/artifacts";

const PROJECT = "2f1c9a3e-6b7d-4c1a-9e2b-1a2b3c4d5e6f";

const script: AgentScript = { title: "测试脚本", hook: "钩子", body_text: "正文", beats: [{ phase: "hook", duration_sec: 2, content: "开场" }] };
const storyboard: AgentStoryboard = {
  title: "测试分镜",
  total_duration_sec: 12,
  shots: [{ index: 1, duration_sec: 4, shot_size: "特写", visual_description: "画面一", dialogue: "台词", ai_warnings: ["手部"] }],
};

beforeEach(() => {
  window.localStorage.clear();
  auth.isDemoMode.mockReturnValue(false);
  auth.apiFetch.mockReset();
});

describe("resolveStorage", () => {
  it("sends real authenticated projects to the gateway", () => {
    expect(resolveStorage(PROJECT)).toBe("api");
  });

  it("falls back to browser storage in demo mode or for non-UUID projects", () => {
    auth.isDemoMode.mockReturnValue(true);
    expect(resolveStorage(PROJECT)).toBe("local");
    auth.isDemoMode.mockReturnValue(false);
    expect(resolveStorage("demo-project")).toBe("local");
    expect(resolveStorage(undefined)).toBe("local");
  });

  it("recognises uuids only", () => {
    expect(isUuid(PROJECT)).toBe(true);
    expect(isUuid("projects/1")).toBe(false);
    expect(isUuid(undefined)).toBe(false);
  });
});

describe("local persistence", () => {
  it("survives a reload, newest first, capped at 50 entries", async () => {
    auth.isDemoMode.mockReturnValue(true);
    for (let i = 0; i < 52; i += 1) {
      await saveGeneration("demo-project", { script: { ...script, title: `脚本 ${i}` }, storyboard }, {});
    }
    const items = await listGenerations("demo-project");
    expect(items).toHaveLength(50);
    expect(items[0].script.title).toBe("脚本 51");
    expect(items[0].storage).toBe("local");
    expect(items[0].storyboard?.shots).toHaveLength(1);
  });

  it("deletes a single entry without touching the others", async () => {
    auth.isDemoMode.mockReturnValue(true);
    const a = await saveGeneration("p1", { script }, {});
    await saveGeneration("p1", { script: { ...script, title: "另一条" } }, {});
    await deleteGeneration("p1", a.id);
    const items = await listGenerations("p1");
    expect(items.map((i) => i.script.title)).toEqual(["另一条"]);
  });

  it("keeps projects isolated from each other", async () => {
    auth.isDemoMode.mockReturnValue(true);
    await saveGeneration("pA", { script }, {});
    await saveGeneration("pB", { script }, {});
    expect(await listGenerations("pA")).toHaveLength(1);
    expect(await listGenerations("pB")).toHaveLength(1);
  });

  it("reports quota failures instead of pretending the save worked", async () => {
    auth.isDemoMode.mockReturnValue(true);
    const failing = vi.spyOn(Storage.prototype, "setItem").mockImplementation(() => {
      throw new Error("QuotaExceeded");
    });
    await expect(saveGeneration("p1", { script }, {})).rejects.toThrow(/存储空间不足/);
    failing.mockRestore();
  });

  it("refuses an empty payload", async () => {
    auth.isDemoMode.mockReturnValue(true);
    await expect(saveGeneration("p1", {}, {})).rejects.toThrow("没有可保存的内容");
  });
});

describe("api persistence", () => {
  it("posts the script, the storyboard and the shots in order", async () => {
    auth.apiFetch
      .mockResolvedValueOnce({ id: "s-1", project_id: PROJECT })
      .mockResolvedValueOnce({ id: "sb-1", project_id: PROJECT, script_id: "s-1" })
      .mockResolvedValueOnce({ ok: true });
    const saved = await saveGeneration(PROJECT, { script, storyboard }, { llm_configured: true, model: "gpt-x" });
    expect(saved.storage).toBe("api");
    // ids come back from the server so later deletes/shots target real rows
    expect(saved.id).toBe("s-1");
    const storyboardBody = JSON.parse((auth.apiFetch.mock.calls[1]?.[1] as { body: string }).body);
    expect(storyboardBody.script_id).toBe("s-1");
    expect(auth.apiFetch.mock.calls.map((c) => [c[0], (c[1] as { method?: string }).method])).toEqual([
      ["/api/v1/scripts", "POST"],
      ["/api/v1/storyboards", "POST"],
      ["/api/v1/storyboards/sb-1/shots", "PUT"],
    ]);
    const shotBody = JSON.parse((auth.apiFetch.mock.calls[2]?.[1] as { body: string }).body);
    expect(shotBody.shots[0]).toMatchObject({ shot_index: 1, duration: 4, shot_type: "特写", dialogue_narration: "台词" });
  });

  it("reads back rows and keeps the verbatim agent payload", async () => {
    auth.apiFetch
      .mockResolvedValueOnce([{ id: "s-1", project_id: PROJECT, created_at: "2026-09-01T00:00:00Z", title: "行脚本", creative_brief: { agent_script: script }, model_info: { llm_configured: true } }])
      .mockResolvedValueOnce([{ id: "sb-1", script_id: "s-1", title: "行分镜", total_duration: 4, shot_count: 1, model_info: { agent_storyboard: storyboard } }]);
    const items = await listGenerations(PROJECT);
    expect(items).toHaveLength(1);
    expect(items[0].llm_configured).toBe(true);
    expect(items[0].script.title).toBe("测试脚本");
    expect(items[0].storyboard?.shots).toHaveLength(1);
  });

  it("falls back to local copies when the gateway is down", async () => {
    auth.isDemoMode.mockReturnValue(true);
    await saveGeneration(PROJECT, { script }, {});
    auth.isDemoMode.mockReturnValue(false);
    auth.apiFetch.mockRejectedValue(new Error("connection refused"));
    const items = await listGenerations(PROJECT);
    expect(items[0].script.title).toBe("测试脚本");
  });

  it("merges without duplicates and stays newest-first", () => {
    const a: SavedGeneration = { id: "a", project_id: "p", created_at: "2026-09-02T00:00:00Z", storage: "api", llm_configured: true, script, storyboard: null };
    const b: SavedGeneration = { ...a, id: "b", created_at: "2026-09-01T00:00:00Z" };
    expect(mergeGenerations([a], [a, b]).map((i) => i.id)).toEqual(["a", "b"]);
  });
});

describe("toShotRows", () => {
  it("maps agent fields onto the persisted column names", () => {
    const [row] = toShotRows(storyboard);
    expect(row).toMatchObject({
      shot_index: 1,
      duration: 4,
      shot_type: "特写",
      subject_description: "画面一",
      dialogue_narration: "台词",
      ai_generation_notes: "手部",
    });
  });

  it("never emits undefined so the API payload stays valid json", () => {
    const [row] = toShotRows({ shots: [{ visual_description: "" }] } as AgentStoryboard);
    expect(Object.values(row).every((v) => v !== undefined)).toBe(true);
    expect(row.subject_description).toBe("未指定");
  });
});
