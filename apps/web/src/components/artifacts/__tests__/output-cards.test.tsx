import { beforeEach, describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { GeneratedScriptOutput, GeneratedStoryboardOutput, SaveStatusChip } from "@/components/artifacts/output-cards";
import { scriptToPlainText } from "@/lib/export-formats";
import type { AgentScript, AgentStoryboard } from "@/lib/agent-output";

const script: AgentScript = {
  title: "口红测评脚本",
  hook: "别再买错色号了",
  hook_variants: [{ hook_type: "痛点", text: "一涂就显黑？" }],
  body_text: "正文内容",
  beats: [{ phase: "hook", duration_sec: 3, content: "开场抛问题", visual_note: "唇部特写" }],
  cta: "评论区扣 1",
  target_duration_sec: 30,
};

const storyboard: AgentStoryboard = {
  title: "口红测评分镜",
  total_duration_sec: 12,
  shot_count: 2,
  aspect_ratio: "9:16",
  visual_style_notes: "自然光微距",
  shots: [
    { index: 1, duration_sec: 4, shot_size: "特写", visual_description: "口红旋出", dialogue: "看这个质地", ai_warnings: ["手指易变形"] },
    { index: 2, duration_sec: 8, shot_size: "中景", visual_description: "上嘴试色" },
  ],
};

beforeEach(() => {
  Object.defineProperty(window.URL, "createObjectURL", { value: vi.fn(() => "blob:mock"), configurable: true });
  Object.defineProperty(window.URL, "revokeObjectURL", { value: vi.fn(), configurable: true });
});

describe("GeneratedScriptOutput", () => {
  it("renders the full script, not a placeholder", () => {
    render(<GeneratedScriptOutput script={script} />);
    expect(screen.getByText("口红测评脚本")).toBeInTheDocument();
    expect(screen.getByText("别再买错色号了")).toBeInTheDocument();
    expect(screen.getByText("一涂就显黑？")).toBeInTheDocument();
    expect(screen.getByText("正文内容")).toBeInTheDocument();
    expect(screen.getByText(/开场抛问题/)).toBeInTheDocument();
    expect(screen.getByText("评论区扣 1")).toBeInTheDocument();
    expect(screen.getByText("1 个节拍 · 30 秒")).toBeInTheDocument();
  });

  it("copies the voice-over text to the clipboard", async () => {
    const writeText = vi.fn().mockResolvedValue(undefined);
    Object.defineProperty(navigator, "clipboard", { value: { writeText }, configurable: true });
    render(<GeneratedScriptOutput script={script} />);
    fireEvent.click(screen.getByRole("button", { name: /复制/ }));
    await waitFor(() => expect(writeText).toHaveBeenCalledWith(scriptToPlainText(script)));
    expect(await screen.findByText("已复制")).toBeInTheDocument();
  });

  it("downloads every declared format with a safe filename", () => {
    const clicks: string[] = [];
    const original = window.HTMLAnchorElement.prototype.click;
    window.HTMLAnchorElement.prototype.click = function (this: HTMLAnchorElement) {
      if (this.download) clicks.push(this.download);
    };
    render(<GeneratedScriptOutput script={script} />);
    fireEvent.click(screen.getByRole("button", { name: /口播 TXT/ }));
    fireEvent.click(screen.getByRole("button", { name: /Markdown/ }));
    fireEvent.click(screen.getByRole("button", { name: /JSON/ }));
    window.HTMLAnchorElement.prototype.click = original;
    expect(clicks).toEqual(["口红测评脚本.txt", "口红测评脚本.md", "口红测评脚本.json"]);
  });
});

describe("GeneratedStoryboardOutput", () => {
  it("renders each shot with its warning", () => {
    render(<GeneratedStoryboardOutput storyboard={storyboard} />);
    expect(screen.getByText("口红测评分镜")).toBeInTheDocument();
    expect(screen.getByText("2 个镜头 · 12 秒 · 9:16")).toBeInTheDocument();
    expect(screen.getByText("自然光微距")).toBeInTheDocument();
    expect(screen.getByText("#1")).toBeInTheDocument();
    expect(screen.getByText(/口红旋出/)).toBeInTheDocument();
    expect(screen.getByText(/看这个质地/)).toBeInTheDocument();
    expect(screen.getByText(/手指易变形/)).toBeInTheDocument();
  });

  it("exports a csv download", () => {
    let downloaded = "";
    const original = window.HTMLAnchorElement.prototype.click;
    window.HTMLAnchorElement.prototype.click = function (this: HTMLAnchorElement) {
      downloaded = this.download;
    };
    render(<GeneratedStoryboardOutput storyboard={storyboard} />);
    fireEvent.click(screen.getByRole("button", { name: /分镜表 CSV/ }));
    window.HTMLAnchorElement.prototype.click = original;
    expect(downloaded).toBe("口红测评分镜.csv");
  });
});

describe("SaveStatusChip", () => {
  it("tells the user where the result was stored", () => {
    render(<SaveStatusChip save={{ state: "saved", storage: "api" }} storage="api" />);
    expect(screen.getByText("已保存到项目库")).toBeInTheDocument();
  });

  it("names browser storage when running in demo mode", () => {
    render(<SaveStatusChip save={{ state: "saved", storage: "local" }} storage="local" />);
    expect(screen.getByText("已存到本浏览器")).toBeInTheDocument();
  });

  it("never hides a failed save", () => {
    render(<SaveStatusChip save={{ state: "error", error: "网络中断" }} storage="api" />);
    expect(screen.getByText(/未保存：网络中断/)).toBeInTheDocument();
  });

  it("flags offline template output", () => {
    render(<SaveStatusChip storage="api" llmConfigured={false} />);
    expect(screen.getByText(/离线模板输出/)).toBeInTheDocument();
  });
});

describe("provenance honesty", () => {
  it("says demo-mode data is not model output", () => {
    render(<SaveStatusChip storage="local" llmConfigured={false} model="demo-mock" />);
    expect(screen.getByText(/演示模式内置数据/)).toBeInTheDocument();
  });

  it("says an offline template is not model output", () => {
    render(<SaveStatusChip storage="api" llmConfigured={false} model="" />);
    expect(screen.getByText(/离线模板输出/)).toBeInTheDocument();
  });
});
