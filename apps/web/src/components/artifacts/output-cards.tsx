"use client";

import { useState } from "react";
import { Check, Clipboard, Download, FileText, Film, Loader2 } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { PromptPackPanel } from "@/components/artifacts/prompt-pack";
import type { StorageKind } from "@/lib/artifacts";
import {
  type AgentBeat,
  type AgentScript,
  type AgentShot,
  type AgentStoryboard,
} from "@/lib/agent-output";
import {
  copyToClipboard,
  downloadText,
  renderExport,
  scriptExports,
  scriptToPlainText,
  storyboardExports,
  storyboardToMarkdown,
  type ExportOption,
} from "@/lib/export-formats";

/**
 * Shared render + export surface for agent output, used both by the chat
 * stream and by the 成果库 panel so a saved result always looks identical to
 * the moment it was generated.
 */

export interface SaveState {
  state: "saving" | "saved" | "error";
  storage?: StorageKind;
  error?: string;
}


/**
 * Copy plus every serialisation the user may actually need downstream.
 * The default copy target is the plain voice-over script, because that is what
 * gets pasted into a teleprompter or a caption field.
 */
export function ExportActions({ kind, payload }: { kind: "script" | "storyboard"; payload: AgentScript | AgentStoryboard }) {
  const [copied, setCopied] = useState(false);
  const options: ExportOption[] = kind === "script"
    ? scriptExports(payload as AgentScript)
    : storyboardExports(payload as AgentStoryboard);
  const copyText = kind === "script"
    ? scriptToPlainText(payload as AgentScript)
    : storyboardToMarkdown(payload as AgentStoryboard);

  async function copy() {
    if (await copyToClipboard(copyText)) {
      setCopied(true);
      window.setTimeout(() => setCopied(false), 1600);
    }
  }

  return (
    <div className="flex shrink-0 flex-wrap justify-end gap-2">
      <Button type="button" size="sm" variant="outline" onClick={copy} className="gap-1.5">
        {copied ? <Check className="h-3.5 w-3.5 text-[#34c759]" /> : <Clipboard className="h-3.5 w-3.5" />}
        {copied ? "已复制" : "复制"}
      </Button>
      {options.map((option) => (
        <Button
          key={option.id}
          type="button"
          size="sm"
          variant="outline"
          className="gap-1.5"
          onClick={() => downloadText(option.filename, renderExport(kind, option.id, payload), option.mime)}
        >
          <Download className="h-3.5 w-3.5" />
          {option.label}
        </Button>
      ))}
    </div>
  );
}

/**
 * Never let a save fail silently: the chip reports where the result went, and
 * flags offline-template answers so nobody mistakes them for model output.
 */
export function SaveStatusChip({ save, llmConfigured, storage, model }: { save?: SaveState; llmConfigured?: boolean; storage: StorageKind; model?: string }) {
  const target = storage === "api" ? "已保存到项目库" : "已存到本浏览器";
  return (
    <div className="mt-2 flex flex-wrap items-center gap-2 text-xs">
      {save?.state === "saving" && <span className="inline-flex items-center gap-1.5 text-[#6e6e73]"><Loader2 className="h-3.5 w-3.5 animate-spin" />保存中…</span>}
      {save?.state === "saved" && (
        <span className="inline-flex items-center gap-1.5 rounded-full border border-[#34c759]/20 bg-[#f1fbf3] px-2.5 py-1 text-[#248a3d]">
          <Check className="h-3.5 w-3.5" />
          {target}
        </span>
      )}
      {save?.state === "error" && (
        <span className="inline-flex items-center gap-1.5 rounded-full border border-[#ff3b30]/20 bg-[#fff4f3] px-2.5 py-1 text-[#c9352c]">
          未保存：{save.error}
        </span>
      )}
      {llmConfigured === false && (
        <span className="inline-flex items-center gap-1.5 rounded-full border border-[#ff9500]/25 bg-[#fff8ec] px-2.5 py-1 text-[#9a6700]">
          {model === "demo-mock" ? "演示模式内置数据（未连接任何模型或后端）" : "离线模板输出（未配置模型 API Key）"}
        </span>
      )}
    </div>
  );
}

export function GeneratedScriptOutput({ script }: { script: AgentScript }) {
  const beats = script.beats || [];
  return (
    <Card className="mt-4 overflow-hidden border-[#007aff]/15 bg-white shadow-apple-md">
      <div className="flex flex-col gap-3 border-b border-black/[0.06] bg-[#f7fbff] px-4 py-4 sm:flex-row sm:items-start sm:justify-between">
        <div className="flex items-start gap-3">
          <div className="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-[10px] bg-[#e8f2ff] text-[#007aff]"><FileText className="h-4 w-4" /></div>
          <div>
            <div className="flex flex-wrap items-center gap-2">
              <span className="text-sm font-semibold text-[#1d1d1f]">完整脚本</span>
              <Badge variant="success">已生成</Badge>
            </div>
            <h4 className="mt-1 text-base font-semibold text-[#1d1d1f]">{script.title || "未命名脚本"}</h4>
            <p className="mt-1 text-xs text-[#6e6e73]">{script.beats?.length || 0} 个节拍{script.target_duration_sec ? ` · ${script.target_duration_sec} 秒` : ""}</p>
          </div>
        </div>
        <ExportActions kind="script" payload={script} />
      </div>
      <div className="space-y-5 px-4 py-5 text-sm text-[#1d1d1f] sm:px-5">
        {script.hook && <section><h5 className="mb-2 font-semibold text-[#ff9500]">🎯 钩子</h5><p className="rounded-[12px] bg-[#fff8ec] px-3 py-3 leading-relaxed">{script.hook}</p></section>}
        {script.hook_variants && script.hook_variants.length > 0 && <section><h5 className="mb-2 font-semibold text-[#6e6e73]">备选钩子</h5><div className="space-y-2">{script.hook_variants.map((variant, index: number) => <div key={index} className="rounded-[12px] bg-[#f5f5f7] px-3 py-2.5"><Badge variant="outline" className="mr-2">{variant.hook_type || `方案 ${index + 1}`}</Badge><span>{variant.text}</span></div>)}</div></section>}
        {script.body_text && <section><h5 className="mb-2 font-semibold text-[#6e6e73]">📝 正文</h5><p className="whitespace-pre-wrap rounded-[12px] bg-[#f5f5f7] px-3 py-3 leading-7">{script.body_text}</p></section>}
        {beats.length > 0 && <section><h5 className="mb-2 font-semibold text-[#6e6e73]">🎬 节拍分解</h5><div className="space-y-2">{beats.map((beat: AgentBeat, index: number) => <div key={index} className="flex gap-3 rounded-[12px] border border-black/[0.06] px-3 py-3"><Badge variant={beat.phase === "hook" ? "danger" : beat.phase === "cta" ? "success" : "outline"} className="mt-0.5 shrink-0">{beat.phase || `节拍 ${index + 1}`} {beat.duration_sec ? `${beat.duration_sec}s` : ""}</Badge><div className="min-w-0"><p className="leading-relaxed">{beat.content}</p>{beat.visual_note && <p className="mt-1 text-xs leading-relaxed text-[#6e6e73]">画面：{beat.visual_note}</p>}</div></div>)}</div></section>}
        {script.cta && <section><h5 className="mb-2 font-semibold text-[#34c759]">📣 CTA</h5><p className="rounded-[12px] bg-[#f1fbf3] px-3 py-3 leading-relaxed">{script.cta}</p></section>}
      </div>
    </Card>
  );
}

export function GeneratedStoryboardOutput({
  storyboard,
  script,
  projectId,
}: {
  storyboard: AgentStoryboard;
  script?: AgentScript | null;
  projectId?: string | null;
}) {

  return (
    <Card className="mt-4 overflow-hidden border-[#af52de]/15 bg-white shadow-apple-md">
      <div className="flex flex-col gap-3 border-b border-black/[0.06] bg-[#fbf7ff] px-4 py-4 sm:flex-row sm:items-start sm:justify-between">
        <div className="flex items-start gap-3">
          <div className="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-[10px] bg-[#f3e8fa] text-[#af52de]"><Film className="h-4 w-4" /></div>
          <div>
            <div className="flex flex-wrap items-center gap-2"><span className="text-sm font-semibold text-[#1d1d1f]">完整分镜表</span><Badge variant="success">已生成</Badge></div>
            <h4 className="mt-1 text-base font-semibold text-[#1d1d1f]">{storyboard.title || "未命名分镜"}</h4>
            <p className="mt-1 text-xs text-[#6e6e73]">{storyboard.shot_count || storyboard.shots?.length || 0} 个镜头{storyboard.total_duration_sec ? ` · ${storyboard.total_duration_sec} 秒` : ""}{storyboard.aspect_ratio ? ` · ${storyboard.aspect_ratio}` : ""}</p>
          </div>
        </div>
        <ExportActions kind="storyboard" payload={storyboard} />
      </div>
      <div className="space-y-4 px-4 py-5 sm:px-5">
        {storyboard.visual_style_notes && <div className="rounded-[12px] bg-[#f5f5f7] px-3 py-3 text-sm leading-relaxed"><strong>视觉风格：</strong>{storyboard.visual_style_notes}</div>}
        <div className="space-y-3">{(storyboard.shots || []).map((shot: AgentShot, index: number) => <div key={index} className="rounded-[14px] border border-black/[0.06] px-3 py-3 text-sm"><div className="mb-2 flex flex-wrap items-center gap-1.5"><span className="mr-1 text-base font-semibold text-[#af52de]">#{shot.index || index + 1}</span><Badge variant="outline">{shot.duration_sec || 0}s</Badge>{shot.shot_size && <Badge variant="outline">{shot.shot_size}</Badge>}{shot.camera_angle && <Badge variant="outline">{shot.camera_angle}</Badge>}{shot.camera_movement && <Badge variant="outline">{shot.camera_movement}</Badge>}</div><p className="leading-relaxed"><strong>画面：</strong>{shot.visual_description || ""}</p>{shot.action_description && <p className="mt-1 text-xs leading-relaxed text-[#6e6e73]"><strong>动作：</strong>{shot.action_description}</p>}{shot.dialogue && <p className="mt-1 leading-relaxed"><strong>台词：</strong>「{shot.dialogue}」</p>}<div className="mt-2 flex flex-wrap gap-x-3 gap-y-1 text-xs text-[#6e6e73]">{shot.lighting && <span>光线：{shot.lighting}</span>}{shot.color_tone && <span>色调：{shot.color_tone}</span>}{shot.transition && <span>转场：{shot.transition}</span>}</div>{shot.ai_warnings && shot.ai_warnings.length > 0 && <p className="mt-2 rounded-[9px] bg-[#fff8ec] px-2 py-1.5 text-xs text-[#9a6700]">⚠️ {shot.ai_warnings.join("；")}</p>}</div>)}</div>
        <PromptPackPanel projectId={projectId} script={script} storyboard={storyboard} />
      </div>
    </Card>
  );
}
