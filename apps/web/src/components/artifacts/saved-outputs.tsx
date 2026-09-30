"use client";

import { useCallback, useEffect, useState } from "react";
import { Check, Download, FileText, Film, Inbox, Loader2, RefreshCw, Trash2 } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { cn } from "@/lib/utils";
import { hasScriptContent, hasStoryboardContent, type AgentScript, type AgentStoryboard } from "@/lib/agent-output";
import { deleteGeneration, listGenerations, resolveStorage, type SavedGeneration } from "@/lib/artifacts";
import { GeneratedScriptOutput, GeneratedStoryboardOutput } from "./output-cards";

type Filter = "all" | "script" | "storyboard";

/**
 * The 成果库: everything the agent generated for this project, read back from
 * whichever backend actually owns it (gateway database or browser storage), so
 * a refresh or a closed tab no longer destroys the user's work.
 */
export function SavedOutputs({ projectId, refreshKey = 0 }: { projectId?: string; refreshKey?: number }) {
  const [items, setItems] = useState<SavedGeneration[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filter, setFilter] = useState<Filter>("all");
  const [expanded, setExpanded] = useState<string | null>(null);
  const storage = resolveStorage(projectId);

  const reload = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      setItems(await listGenerations(projectId));
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  }, [projectId]);

  useEffect(() => { void reload(); }, [reload, refreshKey]);

  async function remove(id: string) {
    try {
      await deleteGeneration(projectId, id);
      setItems((prev) => prev.filter((item) => item.id !== id));
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    }
  }

  const visible = items.filter((item) => {
    if (filter === "script") return hasScriptContent(item.script);
    if (filter === "storyboard") return hasStoryboardContent(item.storyboard);
    return true;
  });

  return (
    <div className="h-full overflow-y-auto bg-[#f5f5f7] px-5 py-6 sm:px-7">
      <div className="mx-auto max-w-4xl">
        <div className="mb-5 flex flex-wrap items-start justify-between gap-3">
          <div>
            <h3 className="text-lg font-semibold tracking-[-0.01em] text-[#1d1d1f]">成果库</h3>
            <p className="mt-1 text-xs text-[#6e6e73]">
              {storage === "api" ? "已连接到 Mago 服务，成果保存在项目数据库中" : "演示模式：成果保存在当前浏览器，换设备或清除浏览器数据会丢失"}
            </p>
          </div>
          <div className="flex items-center gap-2">
            <Badge variant="outline" className="gap-1 border-black/[0.08] bg-white text-[#6e6e73]">
              {storage === "api" ? "服务端存储" : "本地存储"} · {items.length} 条
            </Badge>
            <Button size="sm" variant="outline" className="gap-1.5" onClick={() => void reload()} disabled={loading}>
              <RefreshCw className={cn("h-3.5 w-3.5", loading && "animate-spin")} />刷新
            </Button>
          </div>
        </div>

        <div className="mb-4 flex gap-1 rounded-full border border-black/[0.06] bg-white p-1 shadow-apple-sm">
          {([["all", "全部"], ["script", "脚本"], ["storyboard", "分镜"]] as [Filter, string][]).map(([id, label]) => (
            <button key={id} type="button" onClick={() => setFilter(id)}
              className={cn("flex-1 rounded-full px-3 py-1.5 text-xs font-medium transition-colors",
                filter === id ? "bg-[#007aff] text-white" : "text-[#6e6e73] hover:bg-[#f5f5f7]")}>
              {label}
            </button>
          ))}
        </div>

        {error && (
          <div className="mb-4 flex items-start justify-between gap-3 rounded-[14px] border border-[#ff3b30]/20 bg-[#fff4f3] px-4 py-3 text-sm text-[#c9352c]">
            <span>读取成果失败：{error}</span>
            <Button size="sm" variant="outline" onClick={() => void reload()}>重试</Button>
          </div>
        )}

        {loading && items.length === 0 && (
          <div className="flex items-center justify-center gap-2 py-16 text-sm text-[#86868b]">
            <Loader2 className="h-4 w-4 animate-spin text-[#007aff]" />正在读取…
          </div>
        )}

        {!loading && visible.length === 0 && (
          <Card className="flex flex-col items-center gap-2 rounded-[18px] border-black/[0.06] bg-white px-6 py-14 text-center shadow-apple-sm">
            <div className="flex h-11 w-11 items-center justify-center rounded-[14px] bg-[#f5f5f7] text-[#86868b]"><Inbox className="h-5 w-5" /></div>
            <p className="text-sm font-medium text-[#1d1d1f]">还没有保存的成果</p>
            <p className="max-w-sm text-xs leading-relaxed text-[#86868b]">
              在「对话」里让助手写一条脚本或分镜表，生成后会自动出现在这里，可以直接复制、导出 TXT / Markdown / CSV / JSON。
            </p>
          </Card>
        )}

        <div className="space-y-3">
          {visible.map((item) => {
            const open = expanded === item.id;
            const shots = item.storyboard?.shots?.length || 0;
            const beats = item.script?.beats?.length || 0;
            return (
              <Card key={item.id} className="overflow-hidden rounded-[18px] border-black/[0.06] bg-white shadow-apple-sm">
                <div className="flex flex-wrap items-start justify-between gap-3 px-4 py-4">
                  <div className="min-w-0 flex-1">
                    <div className="flex flex-wrap items-center gap-2">
                      {hasScriptContent(item.script) && (
                        <span className="inline-flex items-center gap-1 text-[10px] text-[#86868b]"><FileText className="h-3 w-3" />脚本</span>
                      )}
                      {hasStoryboardContent(item.storyboard) && (
                        <span className="inline-flex items-center gap-1 text-[10px] text-[#86868b]"><Film className="h-3 w-3" />分镜</span>
                      )}
                      <span className="text-[10px] text-[#aeaeb2]">{formatTime(item.created_at)}</span>
                      {item.llm_configured === false && <Badge variant="warning" className="text-[10px]">离线模板</Badge>}
                    </div>
                    <h4 className="mt-1 truncate text-sm font-semibold text-[#1d1d1f]">
                      {item.script?.title || item.storyboard?.title || "未命名成果"}
                    </h4>
                    <p className="mt-0.5 text-xs text-[#86868b]">
                      {beats ? `${beats} 个节拍` : ""}{beats && shots ? " · " : ""}{shots ? `${shots} 个镜头` : ""}{!beats && !shots ? "无结构化内容" : ""}
                    </p>
                  </div>
                  <div className="flex shrink-0 items-center gap-2">
                    <Button size="sm" variant="outline" className="gap-1.5" onClick={() => setExpanded(open ? null : item.id)}>
                      {open ? "收起" : "查看"}
                    </Button>
                    <Button size="sm" variant="outline" className="gap-1.5 text-[#c9352c]" onClick={() => void remove(item.id)} aria-label="删除成果">
                      <Trash2 className="h-3.5 w-3.5" />
                    </Button>
                  </div>
                </div>
                {open && (
                  <div className="border-t border-black/[0.05] bg-[#fafafa] px-4 pb-5">
                    {hasScriptContent(item.script) && <GeneratedScriptOutput script={item.script as AgentScript} />}
                    {hasStoryboardContent(item.storyboard) && (
                      <GeneratedStoryboardOutput
                        storyboard={item.storyboard as AgentStoryboard}
                        script={item.script as AgentScript | undefined}
                        projectId={item.project_id || projectId}
                      />
                    )}
                    {!hasScriptContent(item.script) && !hasStoryboardContent(item.storyboard) && (
                      <p className="py-6 text-center text-xs text-[#86868b]">这条记录没有可展示的内容。</p>
                    )}
                    {hasScriptContent(item.script) && item.script?.body_text && (
                      <p className="mt-3 flex items-center gap-1.5 text-[11px] text-[#aeaeb2]"><Check className="h-3 w-3" />导出的正文与生成时完全一致，可用下方按钮取 TXT / Markdown / JSON。</p>
                    )}
                    {!hasStoryboardContent(item.storyboard) && storage === "api" && (
                      <p className="mt-3 flex items-center gap-1.5 text-[11px] text-[#aeaeb2]"><Download className="h-3 w-3" />分镜表需在服务端保存后才会出现在这里。</p>
                    )}
                  </div>
                )}
              </Card>
            );
          })}
        </div>
      </div>
    </div>
  );
}

function formatTime(iso: string): string {
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return iso;
  return date.toLocaleString("zh-CN", { month: "2-digit", day: "2-digit", hour: "2-digit", minute: "2-digit" });
}
