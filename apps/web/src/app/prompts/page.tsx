"use client";

import { useCallback, useEffect, useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Copy, Download, Loader2, Wand2 } from "lucide-react";
import { promptsApi, type Prompt, type PromptPackage } from "@/lib/api";

export default function PromptsPage() {
  const [projectId, setProjectId] = useState("");
  const [packages, setPackages] = useState<PromptPackage[]>([]);
  const [selected, setSelected] = useState<{ pkg: PromptPackage; prompts: Prompt[] } | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [copied, setCopied] = useState<string | null>(null);

  const loadPackages = useCallback(async (value = projectId) => {
    if (!value.trim()) { setError("请先输入项目 ID"); return; }
    setLoading(true); setError(null);
    try { setPackages(await promptsApi.listPackages(value.trim())); setSelected(null); }
    catch (err) { setError(err instanceof Error ? err.message : "提示词包加载失败"); }
    finally { setLoading(false); }
  }, [projectId]);

  useEffect(() => {
    const value = new URLSearchParams(window.location.search).get("project_id") || "";
    if (value) { setProjectId(value); void loadPackages(value); }
  }, [loadPackages]);

  async function openPackage(pkg: PromptPackage) {
    setError(null);
    try { const result = await promptsApi.getPackage(pkg.id); setSelected({ pkg, prompts: result.prompts }); }
    catch (err) { setError(err instanceof Error ? err.message : "提示词详情加载失败"); }
  }

  async function copy(id: string, value: string) {
    try {
      if (navigator.clipboard?.writeText) {
        await navigator.clipboard.writeText(value);
      } else {
        const textarea = document.createElement("textarea");
        textarea.value = value;
        textarea.setAttribute("readonly", "true");
        textarea.style.position = "fixed";
        textarea.style.opacity = "0";
        document.body.appendChild(textarea);
        textarea.select();
        const copied = document.execCommand("copy");
        document.body.removeChild(textarea);
        if (!copied) throw new Error("浏览器拒绝了复制操作");
      }
      setCopied(id);
      window.setTimeout(() => setCopied(null), 2000);
    } catch (err) {
      setError(err instanceof Error ? err.message : "复制失败，请手动选择文本复制");
    }
  }

  function exportJSON() {
    if (!selected) return;
    const blob = new Blob([JSON.stringify(selected, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a"); anchor.href = url; anchor.download = `${selected.pkg.name || "prompt-package"}.json`; anchor.click(); URL.revokeObjectURL(url);
  }

  return (
    <div className="p-6 max-w-6xl mx-auto space-y-6">
      <div className="flex items-center justify-between gap-4 flex-wrap"><div><h1 className="text-2xl font-bold flex items-center gap-2"><Wand2 className="w-6 h-6" />提示词导出</h1><p className="text-sm text-muted-foreground mt-1">从真实项目提示词包中查看、复制和导出生成结果</p></div><Button variant="outline" className="gap-2" onClick={exportJSON} disabled={!selected}><Download className="w-4 h-4" />导出 JSON</Button></div>
      <Card className="p-4"><div className="flex gap-2"><input className="flex-1 px-3 py-2 rounded-lg border border-border bg-background text-sm" value={projectId} onChange={(e) => setProjectId(e.target.value)} placeholder="输入项目 ID（也可通过 ?project_id= 传入）" /><Button onClick={() => void loadPackages()} disabled={loading}>{loading && <Loader2 className="w-4 h-4 mr-2 animate-spin" />}加载提示词包</Button></div></Card>
      {error && <p className="text-sm text-destructive" role="alert">{error}</p>}
      {packages.length === 0 && !loading ? <Card className="py-12 text-center text-muted-foreground">暂无提示词包。请确认项目 ID 正确，或先在项目中生成提示词。</Card> : <div className="grid grid-cols-1 md:grid-cols-3 gap-4">{packages.map((pkg) => <button key={pkg.id} className="text-left" onClick={() => void openPackage(pkg)}><Card className={`p-4 h-full hover:border-primary transition ${selected?.pkg.id === pkg.id ? "border-primary" : ""}`}><p className="font-medium">{pkg.name || "未命名提示词包"}</p><div className="flex gap-2 mt-2"><Badge variant="outline">{pkg.status}</Badge><Badge variant="outline">{pkg.total_shots} 个镜头</Badge></div><p className="text-xs text-muted-foreground mt-2">模型：{(pkg.selected_models || []).join(", ") || "未设置"}</p></Card></button>)}</div>}
      {selected && <div className="space-y-4"><h2 className="font-semibold">{selected.pkg.name} · 提示词列表</h2>{selected.prompts.length === 0 ? <Card className="p-6 text-sm text-muted-foreground">该提示词包还没有生成结果。</Card> : selected.prompts.map((prompt) => <Card key={prompt.id} className="p-4"><div className="flex items-center justify-between mb-2"><div className="flex gap-2"><Badge>镜头 {prompt.shot_id}</Badge><Badge variant="outline">{prompt.model_id}</Badge></div><Button size="sm" variant="ghost" className="gap-1" onClick={() => void copy(prompt.id, prompt.positive_prompt)}><Copy className="w-3 h-3" />{copied === prompt.id ? "已复制" : "复制"}</Button></div><pre className="bg-muted/50 rounded-lg p-3 text-sm whitespace-pre-wrap font-mono">{prompt.positive_prompt}</pre>{prompt.negative_prompt && <p className="mt-2 text-xs text-red-600">负向词：{prompt.negative_prompt}</p>}</Card>)}</div>}
    </div>
  );
}
