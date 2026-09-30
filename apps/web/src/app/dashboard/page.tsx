"use client";

import { useState } from "react";
import { ChatInterface } from "@/components/chat/chat-interface";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Sparkles, Plus, FolderOpen, TrendingUp, Lightbulb, ArrowUpRight, Clock3 } from "lucide-react";
import { useRouter } from "next/navigation";

const recentProjects = [
  { name: "美妆口红种草视频", status: "脚本中", updated: "2小时前", color: "#ff9f0a" },
  { name: "iPhone16开箱评测", status: "提示词完成", updated: "昨天", color: "#34c759" },
  { name: "秋日穿搭分享", status: "草稿", updated: "3天前", color: "#af52de" },
];

export default function DashboardPage() {
  const router = useRouter();
  const [showChat, setShowChat] = useState(true);

  return (
    <div className="min-h-full bg-[#f5f5f7] p-4 sm:p-6">
      <div className="grid min-h-[calc(100vh-132px)] grid-cols-1 gap-5 xl:grid-cols-[minmax(0,1fr)_292px]">
        <section className="flex min-h-[680px] min-w-0 flex-col overflow-hidden rounded-[24px] border border-black/[0.055] bg-white shadow-[0_3px_16px_rgba(0,0,0,0.04)]">
          <div className="flex h-[72px] shrink-0 items-center justify-between border-b border-black/[0.05] px-5 sm:px-6">
            <div className="flex items-center gap-3">
              <div className="flex h-9 w-9 items-center justify-center rounded-[11px] bg-[#e8f2ff] text-[#007aff]"><Sparkles className="h-[18px] w-[18px]" /></div>
              <div><h1 className="text-[17px] font-semibold tracking-[-0.02em] text-[#1d1d1f]">创意工作台</h1><p className="text-[11px] text-[#86868b]">和 Mago 一起，把灵感变成作品</p></div>
            </div>
            <Button variant="outline" size="sm" onClick={() => setShowChat(true)}><Plus className="mr-1.5 h-3.5 w-3.5" />新对话</Button>
          </div>
          <div className="min-h-0 flex-1">{showChat ? <ChatInterface /> : <div className="flex h-full items-center justify-center"><div className="text-center"><div className="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-[20px] bg-[#e8f2ff] text-[#007aff]"><Sparkles className="h-8 w-8" /></div><h2 className="mb-2 text-2xl font-semibold">开始新的创作</h2><p className="mb-6 text-sm text-[#86868b]">告诉 AI 你想做什么，让灵感开始流动</p><Button size="lg" onClick={() => setShowChat(true)}><Plus className="mr-2 h-5 w-5" />新对话</Button></div></div>}</div>
        </section>

        <aside className="space-y-4 xl:overflow-y-auto">
          <Card className="overflow-hidden p-0">
            <div className="flex items-center justify-between border-b border-black/[0.05] px-5 py-4"><h2 className="flex items-center gap-2 text-[14px] font-semibold"><FolderOpen className="h-4 w-4 text-[#007aff]" />最近项目</h2><button type="button" onClick={() => router.push("/projects")} className="text-[12px] font-medium text-[#007aff] hover:underline">全部</button></div>
            <div className="p-2">{recentProjects.map((project) => <button type="button" key={project.name} onClick={() => router.push("/projects")} className="group flex w-full items-center gap-3 rounded-[12px] px-3 py-3 text-left transition-colors hover:bg-[#f5f5f7]"><span className="h-2.5 w-2.5 shrink-0 rounded-full" style={{ backgroundColor: project.color }} /><span className="min-w-0 flex-1"><span className="block truncate text-[13px] font-medium text-[#1d1d1f]">{project.name}</span><span className="mt-0.5 block text-[11px] text-[#86868b]">{project.status} · {project.updated}</span></span><ArrowUpRight className="h-3.5 w-3.5 text-[#c7c7cc] opacity-0 transition-opacity group-hover:opacity-100" /></button>)}</div>
            <div className="border-t border-black/[0.05] p-3"><Button variant="ghost" size="sm" className="w-full text-[12px]" onClick={() => router.push("/projects")}><Plus className="mr-1.5 h-3.5 w-3.5" />新建项目</Button></div>
          </Card>

          <Card className="p-5"><h2 className="mb-4 flex items-center gap-2 text-[14px] font-semibold"><TrendingUp className="h-4 w-4 text-[#ff9f0a]" />今日灵感</h2><div className="space-y-3 text-[12px] leading-relaxed text-[#515154]"><div className="flex gap-2.5"><span className="mt-0.5">🔥</span><span>秋日氛围感穿搭视频热度上升 200%</span></div><div className="flex gap-2.5"><span className="mt-0.5">🎬</span><span>AI 电影感调色教程近期高互动</span></div><div className="flex gap-2.5"><span className="mt-0.5">💡</span><span>“沉浸式”类视频完播率高于均值 35%</span></div></div><button type="button" onClick={() => router.push("/trends")} className="mt-4 flex items-center gap-1 text-[12px] font-medium text-[#007aff]">查看更多 <ArrowUpRight className="h-3.5 w-3.5" /></button></Card>

          <Card className="p-5"><h2 className="mb-4 flex items-center gap-2 text-[14px] font-semibold"><Lightbulb className="h-4 w-4 text-[#af52de]" />快捷操作</h2><div className="space-y-2"><Button variant="secondary" size="sm" className="w-full justify-start text-[12px]" onClick={() => router.push("/topics")}><Lightbulb className="mr-2 h-3.5 w-3.5 text-[#af52de]" />AI智能选题</Button><Button variant="secondary" size="sm" className="w-full justify-start text-[12px]" onClick={() => router.push("/viral")}><TrendingUp className="mr-2 h-3.5 w-3.5 text-[#ff9f0a]" />拆解爆款视频</Button><Button variant="secondary" size="sm" className="w-full justify-start text-[12px]" onClick={() => router.push("/projects")}><Clock3 className="mr-2 h-3.5 w-3.5 text-[#007aff]" />查看任务记录</Button></div></Card>
        </aside>
      </div>
    </div>
  );
}
