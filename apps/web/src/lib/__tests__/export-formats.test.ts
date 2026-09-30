import { describe, expect, it } from "vitest";
import {
  renderExport,
  safeSlug,
  scriptExports,
  scriptToMarkdown,
  scriptToPlainText,
  storyboardExports,
  storyboardToCsv,
  storyboardToMarkdown,
  beatLabel,
} from "@/lib/export-formats";
import type { AgentScript, AgentStoryboard } from "@/lib/agent-output";

const script: AgentScript = {
  title: '口红测评: "2026" 春季',
  hook: "别再买错口红色号了",
  hook_variants: [{ hook_type: "痛点", text: "涂显黑？" }],
  body_text: "第一段正文\n第二段正文",
  beats: [
    { phase: "hook", duration_sec: 3, content: "抛出问题", visual_note: "特写嘴唇" },
    { phase: "cta", content: "点关注" },
  ],
  cta: "评论区扣 1 领取色号表",
  target_duration_sec: 30,
  target_platform: "抖音",
};

const storyboard: AgentStoryboard = {
  title: "口红测评分镜",
  total_duration_sec: 30,
  aspect_ratio: "9:16",
  visual_style_notes: "自然光 + 微距",
  shots: [
    { index: 1, duration_sec: 3, shot_size: "特写", visual_description: '含逗号,和"引号"的描述', dialogue: "台词一", transition: "cut" },
    { duration_sec: 4, shot_size: "中景", visual_description: "第二镜", ai_warnings: ["手部细节易崩"] },
  ],
};

describe("scriptToPlainText", () => {
  it("keeps every section without markdown noise", () => {
    const text = scriptToPlainText(script);
    expect(text).toContain("【钩子】\n别再买错口红色号了");
    expect(text).toContain("【正文】");
    expect(text).toContain("1. (hook · 3s) 抛出问题");
    expect(text).toContain("【CTA】\n评论区扣 1 领取色号表\n");
    expect(text).not.toContain("**");
    expect(text).not.toContain("# ");
  });

  it("tolerates an empty payload", () => {
    expect(scriptToPlainText({} as AgentScript)).toBe("未命名脚本\n");
  });
});

describe("scriptToMarkdown", () => {
  it("renders headings and beats", () => {
    const md = scriptToMarkdown(script);
    expect(md.startsWith('# 口红测评: "2026" 春季\n')).toBe(true);
    expect(md).toContain("> 目标时长 30 秒 · 抖音");
    expect(md).toContain("- **hook · 3s** — 抛出问题（画面：特写嘴唇）");
    expect(md).toContain("- **cta** — 点关注");
    expect(md.trimEnd().endsWith("发布前请人工复核。")).toBe(true);
  });
});

describe("storyboard exports", () => {
  it("markdown lists every shot field", () => {
    const md = storyboardToMarkdown(storyboard);
    expect(md).toContain("## 镜头 1（3s）");
    expect(md).toContain("- 台词：「台词一」");
    expect(md).toContain("- ⚠️ AI 风险：手部细节易崩");
  });

  it("csv uses CRLF, a header, and RFC escaping", () => {
    const csv = storyboardToCsv(storyboard);
    const [header, first] = csv.split("\r\n");
    expect(header.startsWith("镜头序号,时长(秒),景别,")).toBe(true);
    expect(csv.endsWith("\r\n")).toBe(true);
    // the embedded comma + quotes must be doubled and wrapped
    expect(first).toContain('"含逗号,和""引号""的描述"');
    expect(csv.split("\r\n").length).toBe(4); // header + 2 rows + trailing
  });

  it("fills the shot index when the model omitted it", () => {
    const csv = storyboardToCsv(storyboard);
    expect(csv.split("\r\n")[2]?.startsWith("2,4,中景")).toBe(true);
  });

  it("renders an empty storyboard as a header-only csv", () => {
    expect(storyboardToCsv({ shots: [] } as AgentStoryboard).split("\r\n").length).toBe(2);
  });
});

describe("file naming", () => {
  it("strips path separators and unsafe characters", () => {
    expect(safeSlug('a/b\\c:d*e?f"g<h>i|j')).toBe("abcdefghij");
    expect(safeSlug("  口红  测评  ")).toBe("口红-测评");
    expect(safeSlug("")).toBe("mago-export");
    expect(safeSlug("x".repeat(200))).toHaveLength(60);
  });

  it("derives filenames from the title", () => {
    expect(scriptExports(script).map((o) => o.filename)).toEqual([
      "口红测评-2026-春季.txt",
      "口红测评-2026-春季.md",
      "口红测评-2026-春季.json",
    ]);
    expect(storyboardExports(storyboard).map((o) => o.id)).toEqual(["csv", "md", "json"]);
  });
});

describe("renderExport", () => {
  it("routes script formats", () => {
    expect(renderExport("script", "txt", script)).toBe(scriptToPlainText(script));
    expect(renderExport("script", "md", script)).toBe(scriptToMarkdown(script));
    expect(JSON.parse(renderExport("script", "json", script))).toMatchObject({ title: script.title });
  });

  it("routes storyboard formats", () => {
    expect(renderExport("storyboard", "csv", storyboard)).toBe(storyboardToCsv(storyboard));
    expect(renderExport("storyboard", "md", storyboard)).toBe(storyboardToMarkdown(storyboard));
    expect(JSON.parse(renderExport("storyboard", "json", storyboard)).shots).toHaveLength(2);
  });
});

describe("beatLabel", () => {
  it("falls back to a numbered label", () => {
    expect(beatLabel({ content: "x" }, 1)).toBe("节拍 2");
    expect(beatLabel({ phase: "body", duration_sec: 5 }, 0)).toBe("body · 5s");
  });
});
