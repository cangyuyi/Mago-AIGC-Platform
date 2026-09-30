"use client";

import { useEffect, useMemo, useState } from "react";
import { Check, ChevronDown, Clipboard, Download, Loader2, Sparkles, Wand2 } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import type { AgentScript, AgentStoryboard } from "@/lib/agent-output";
import {
  type PromptExportOption,
  type PromptItem,
  type PromptModel,
  type PromptPackage,
  defaultModelSelection,
  downloadPromptPack,
  formatParameters,
  groupShotIndexes,
  listPromptModels,
  modelLanguage,
  promptPackExports,
  requestPromptPack,
} from "@/lib/prompt-pack";
import { copyToClipboard } from "@/lib/export-formats";

/**
 * The output creators actually need: per-model prompts they can paste into
 * 可灵 / Midjourney / Runway today. Rendered from the storyboard, so it works
 * with an offline-template storyboard and with a model-written one alike.
 */

export function PromptPackPanel({
  projectId,
  script,
  storyboard,
}: {
  projectId?: string | null;
  script?: AgentScript | null;
  storyboard: AgentStoryboard;
}) {
  const [models, setModels] = useState<PromptModel[]>([]);
  const [selected, setSelected] = useState<string[]>([]);
  const [pkg, setPkg] = useState<PromptPackage | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [openShots, setOpenShots] = useState<Record<number, boolean>>({});

  const shots = storyboard.shots || [];

  // Derived from the engine's own model list so the hint never drifts when
  // models are added to model_configs.json.
  const zhNames = useMemo(
    () => models.filter((model) => modelLanguage(model) === "zh").map((model) => model.display_name).join("、"),
    [models],
  );
  const enNames = useMemo(
    () => models.filter((model) => modelLanguage(model) === "en").map((model) => model.display_name).join("、"),
    [models],
  );

  useEffect(() => {
    let active = true;
    listPromptModels().then((list) => {
      if (!active) return;
      setModels(list);
      setSelected((current) => (current.length ? current : defaultModelSelection(list)));
    });
    return () => {
      active = false;
    };
  }, []);

  async function generate() {
    setLoading(true);
    setError("");
    try {
      const result = await requestPromptPack({ projectId, storyboard, script, models: selected });
      setPkg(result.package);
      setOpenShots({});
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "提示词包生成失败");
    } finally {
      setLoading(false);
    }
  }

  function toggle(modelId: string) {
    setError("");
    setSelected((current) =>
      current.includes(modelId) ? current.filter((entry) => entry !== modelId) : [...current, modelId],
    );
  }

  const grouped = useMemo(() => {
    if (!pkg) return [];
    return groupShotIndexes(pkg.prompts).map((shotIndex) => ({
      shotIndex,
      items: pkg.prompts.filter((item) => item.shot_index === shotIndex),
    }));
  }, [pkg]);

  return (
    <Card className="mt-4 overflow-hidden border-[#ff9500]/15 bg-white shadow-apple-md">
      <div className="border-b border-black/[0.06] bg-[#fffaf2] px-4 py-4 sm:px-5">
        <div className="flex items-start gap-3">
          <div className="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-[10px] bg-[#ffeed6] text-[#b26a00]">
            <Wand2 className="h-4 w-4" />
          </div>
          <div className="min-w-0">
            <div className="flex flex-wrap items-center gap-2">
              <span className="text-sm font-semibold text-[#1d1d1f]">出片提示词包</span>
              <Badge variant="outline">{shots.length} 个镜头</Badge>
            </div>
            <p className="mt-1 text-xs leading-relaxed text-[#6e6e73]">
              按每个模型的语法模板生成正向/负向提示词与参数，可直接粘贴到生成工具。由 Mago
              提示词引擎模板化产出（不消耗模型额度、无需 API Key），发布前请人工微调。
            </p>
          </div>
        </div>
      </div>

      <div className="space-y-4 px-4 py-5 sm:px-5">
        {models.length > 0 ? (
          <div>
            <div className="mb-2 text-xs font-medium text-[#6e6e73]">目标模型（可多选）</div>
            <div className="flex flex-wrap gap-2">
              {models.map((model) => {
                const active = selected.includes(model.model_id);
                return (
                  <button
                    key={model.model_id}
                    type="button"
                    onClick={() => toggle(model.model_id)}
                    aria-pressed={active}
                    className={`inline-flex items-center gap-1.5 rounded-full border px-3 py-1.5 text-xs transition-colors ${
                      active
                        ? "border-[#007aff] bg-[#eaf4ff] text-[#0040a8]"
                        : "border-black/[0.08] bg-white text-[#1d1d1f] hover:bg-[#f5f5f7]"
                    }`}
                  >
                    <span className={`h-1.5 w-1.5 rounded-full ${model.prompt_type === "video" ? "bg-[#af52de]" : "bg-[#34c759]"}`} />
                    {model.display_name}
                    <span className="rounded-md bg-black/[0.05] px-1 py-px font-mono text-[10px] text-[#6e6e73]">
                      {modelLanguage(model) === "zh" ? "中文" : "EN"}
                    </span>
                    {active && <Check className="h-3 w-3" />}
                  </button>
                );
              })}
            </div>
          </div>
        ) : (
          <p className="text-xs text-[#6e6e73]">模型清单加载中…</p>
        )}
        {models.length > 0 && (
          <p className="text-[11px] leading-relaxed text-[#8e8e93]">
            标「中文」的模型（{zhNames}）可直接用中文提示词；标「EN」的模型（{enNames}）需先译成英文再生成，导出时每条都会单独提醒。
          </p>
        )}

        <div className="flex flex-wrap items-center gap-3">
          <Button
            type="button"
            size="sm"
            onClick={generate}
            disabled={loading || shots.length === 0 || selected.length === 0}
            className="gap-1.5 rounded-full bg-[#007aff] px-4 text-white hover:bg-[#0a7cff] disabled:bg-[#c7c7cc]"
          >
            {loading ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Sparkles className="h-3.5 w-3.5" />}
            {pkg ? "重新生成" : "生成提示词包"}
          </Button>
          {shots.length === 0 && <span className="text-xs text-[#c9352c]">还没有分镜表，请先生成分镜表</span>}
          {shots.length > 0 && selected.length === 0 && <span className="text-xs text-[#c9352c]">至少选择一个模型</span>}
        </div>

        {error && (
          <div className="rounded-[12px] border border-[#ff3b30]/20 bg-[#fff4f3] px-3 py-2.5 text-xs leading-relaxed text-[#c9352c]">
            {error}
          </div>
        )}

        {pkg && (
          <div className="space-y-3">
            <div className="flex flex-wrap items-center justify-between gap-2 rounded-[12px] bg-[#f5f5f7] px-3 py-2.5 text-xs text-[#6e6e73]">
              <span>
                {pkg.total_shots} 个镜头 · {pkg.prompts.length} 条提示词 · 比例 {pkg.aspect_ratio || "—"}
              </span>
              <PromptPackExportBar pkg={pkg} />
            </div>
            {grouped.map(({ shotIndex, items }) => {
              const open = openShots[shotIndex] !== false;
              return (
                <div key={shotIndex} className="overflow-hidden rounded-[14px] border border-black/[0.06]">
                  <button
                    type="button"
                    onClick={() => setOpenShots((current) => ({ ...current, [shotIndex]: !open }))}
                    aria-expanded={open}
                    className="flex w-full items-center justify-between gap-2 bg-white px-3 py-2.5 text-left text-sm hover:bg-[#f5f5f7]"
                  >
                    <span className="font-semibold text-[#1d1d1f]">
                      镜头 {shotIndex}
                      <span className="ml-2 text-xs font-normal text-[#6e6e73]">{items.length} 个模型</span>
                    </span>
                    <ChevronDown className={`h-4 w-4 shrink-0 text-[#6e6e73] transition-transform ${open ? "rotate-180" : ""}`} />
                  </button>
                  {open && (
                    <div className="space-y-3 border-t border-black/[0.06] bg-[#fafafa] p-3">
                      {items.map((item) => (
                        <PromptItemCard key={`${item.model_id}-${item.shot_index}`} item={item} />
                      ))}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </div>
    </Card>
  );
}

function PromptItemCard({ item }: { item: PromptItem }) {
  const [copied, setCopied] = useState<"positive" | "negative" | "all" | "">("");

  async function copy(text: string, target: "positive" | "negative" | "all") {
    if (await copyToClipboard(text)) {
      setCopied(target);
      window.setTimeout(() => setCopied(""), 1600);
    }
  }

  const combined = [
    `正向：${item.positive_prompt}`,
    item.negative_prompt ? `负向：${item.negative_prompt}` : "",
    `参数：${formatParameters(item)}`,
  ]
    .filter(Boolean)
    .join("\n");

  return (
    <div className="rounded-[12px] border border-black/[0.06] bg-white px-3 py-3">
      <div className="mb-2 flex flex-wrap items-center gap-2">
        <span className="text-sm font-semibold text-[#1d1d1f]">{item.model_name}</span>
        <Badge variant={item.prompt_type === "video" ? "warning" : "outline"}>
          {item.prompt_type === "video" ? "视频" : "图像"}
        </Badge>
        <span className="text-[11px] text-[#8e8e93]">{item.language === "zh" ? "中文提示词" : "英文提示词"}</span>
      </div>

      <PromptField
        label="正向提示词"
        value={item.positive_prompt}
        copied={copied === "positive"}
        onCopy={() => copy(item.positive_prompt, "positive")}
      />
      {item.negative_prompt && (
        <PromptField
          label="负向提示词"
          value={item.negative_prompt}
          tone="muted"
          copied={copied === "negative"}
          onCopy={() => copy(item.negative_prompt, "negative")}
        />
      )}

      <div className="mt-2 flex flex-wrap gap-1.5">
        {Object.entries(item.parameters).map(([key, value]) => (
          <span
            key={key}
            className="rounded-md bg-[#f5f5f7] px-1.5 py-0.5 font-mono text-[11px] text-[#48484a]"
          >
            {key}={Array.isArray(value) ? value.join("|") : String(value)}
          </span>
        ))}
      </div>

      {(item.warnings || []).map((warning) => (
        <p key={warning} className="mt-2 rounded-[9px] bg-[#fff8ec] px-2 py-1.5 text-[11px] leading-relaxed text-[#9a6700]">
          ⚠️ {warning}
        </p>
      ))}

      <div className="mt-2 flex justify-end">
        <Button type="button" size="sm" variant="ghost" className="gap-1.5 text-xs" onClick={() => copy(combined, "all")}>
          {copied === "all" ? <Check className="h-3.5 w-3.5 text-[#34c759]" /> : <Clipboard className="h-3.5 w-3.5" />}
          {copied === "all" ? "已复制" : "复制整条"}
        </Button>
      </div>
    </div>
  );
}

function PromptField({
  label,
  value,
  copied,
  onCopy,
  tone = "default",
}: {
  label: string;
  value: string;
  copied: boolean;
  onCopy: () => void;
  tone?: "default" | "muted";
}) {
  return (
    <div className="mt-2">
      <div className="mb-1 flex items-center justify-between gap-2">
        <span className="text-[11px] font-medium text-[#6e6e73]">{label}</span>
        <button
          type="button"
          onClick={onCopy}
          className="inline-flex items-center gap-1 rounded-full border border-black/[0.08] px-2 py-0.5 text-[11px] text-[#007aff] hover:bg-[#eaf4ff]"
        >
          {copied ? <Check className="h-3 w-3 text-[#34c759]" /> : <Clipboard className="h-3 w-3" />}
          {copied ? "已复制" : "复制"}
        </button>
      </div>
      <p
        className={`whitespace-pre-wrap break-words rounded-[10px] px-2.5 py-2 text-[13px] leading-relaxed ${
          tone === "muted" ? "bg-[#f5f5f7] text-[#48484a]" : "bg-[#fbfbfd] text-[#1d1d1f]"
        }`}
      >
        {value}
      </p>
    </div>
  );
}

function PromptPackExportBar({ pkg }: { pkg: PromptPackage }) {
  const options: PromptExportOption[] = promptPackExports(pkg);
  return (
    <div className="flex flex-wrap items-center gap-2">
      {options.map((option) => (
        <Button
          key={option.label}
          type="button"
          size="sm"
          variant="outline"
          className="h-7 gap-1.5 rounded-full px-2.5 text-[11px]"
          onClick={() => downloadPromptPack(pkg, option)}
        >
          <Download className="h-3 w-3" />
          {option.label}
        </Button>
      ))}
    </div>
  );
}
