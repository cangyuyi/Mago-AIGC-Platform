"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { Plus, FolderOpen, ArrowRight, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { projectsApi, type Project } from "@/lib/api";
import { formatDate } from "@/lib/utils";

export default function ProjectsPage() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [loading, setLoading] = useState(true);
  const [showNew, setShowNew] = useState(false);
  const [newName, setNewName] = useState("");
  const [newDesc, setNewDesc] = useState("");
  const [creating, setCreating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadProjects();
  }, []);

  async function loadProjects() {
    setLoading(true);
    setError(null);
    try {
      const data = await projectsApi.list(1, 50);
      setProjects(data.items ?? []);
    } catch (e) {
      setProjects([]);
      setError(e instanceof Error ? e.message : "项目加载失败，请稍后重试");
    } finally {
      setLoading(false);
    }
  }

  async function createProject() {
    if (!newName.trim()) return;
    setCreating(true);
    try {
      await projectsApi.create({ name: newName, description: newDesc, aspect_ratio: "9:16" });
      setNewName("");
      setNewDesc("");
      setShowNew(false);
      await loadProjects();
    } catch (e) {
      setError(e instanceof Error ? e.message : "项目创建失败，请稍后重试");
    } finally {
      setCreating(false);
    }
  }

  const statusMap: Record<string, { label: string; variant: "default" | "success" | "warning" | "outline" }> = {
    draft: { label: "草稿", variant: "outline" },
    in_progress: { label: "进行中", variant: "default" },
    completed: { label: "已完成", variant: "success" },
    archived: { label: "已归档", variant: "warning" },
  };

  return (
    <div className="p-8 max-w-6xl mx-auto">
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-2xl font-bold">我的项目</h1>
          <p className="text-sm text-muted-foreground mt-1">管理你的所有视频创作项目</p>
        </div>
        <Button variant="primary" onClick={() => setShowNew(true)}>
          <Plus className="w-4 h-4 mr-2" /> 新建项目
        </Button>
      </div>

      {error && (
        <Card className="mb-6 border-destructive/40 bg-destructive/5">
          <p className="p-4 text-sm text-destructive" role="alert">{error}</p>
        </Card>
      )}

      {showNew && (
        <Card className="p-6 mb-6">
          <h3 className="font-semibold mb-4">新建项目</h3>
          <div className="space-y-3">
            <div>
              <label className="block text-sm font-medium mb-1">项目名称</label>
              <Input
                value={newName}
                onChange={(e) => setNewName(e.target.value)}
                placeholder="给你的项目起个名字"
              />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">描述（可选）</label>
              <Input
                value={newDesc}
                onChange={(e) => setNewDesc(e.target.value)}
                placeholder="简单描述这个视频项目"
              />
            </div>
            <div className="flex gap-2 justify-end">
              <Button variant="ghost" onClick={() => setShowNew(false)}>取消</Button>
              <Button variant="primary" onClick={createProject} disabled={creating || !newName.trim()}>
                {creating ? <Loader2 className="w-4 h-4 animate-spin" /> : "创建"}
              </Button>
            </div>
          </div>
        </Card>
      )}

      {loading ? (
        <div className="text-center py-20 text-muted-foreground">
          <Loader2 className="w-8 h-8 animate-spin mx-auto mb-2" />
          加载中...
        </div>
      ) : projects.length === 0 ? (
        <div className="text-center py-20">
          <FolderOpen className="w-16 h-16 text-muted-foreground/30 mx-auto mb-4" />
          <h3 className="text-lg font-medium mb-2">还没有项目</h3>
          <p className="text-sm text-muted-foreground mb-4">点击&quot;新建项目&quot;开始你的第一个AI创意视频</p>
          <Button variant="primary" onClick={() => setShowNew(true)}>
            <Plus className="w-4 h-4 mr-2" /> 新建项目
          </Button>
        </div>
      ) : (
        <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
          {projects.map((p) => {
            const status = statusMap[p.status] || statusMap.draft;
            return (
              <Link key={p.id} href={`/projects/${p.id}`}>
                <Card className="p-5 hover:border-primary/50 hover:shadow-md transition-all cursor-pointer group">
                  <div className="flex items-start justify-between mb-3">
                    <h3 className="font-semibold leading-tight group-hover:text-primary transition-colors">
                      {p.name}
                    </h3>
                    <Badge variant={status.variant}>{status.label}</Badge>
                  </div>
                  {p.description && (
                    <p className="text-sm text-muted-foreground mb-3 line-clamp-2">{p.description}</p>
                  )}
                  <div className="flex items-center justify-between text-xs text-muted-foreground">
                    <span>{p.aspect_ratio}</span>
                    <span>{formatDate(p.updated_at)}</span>
                  </div>
                  <div className="mt-3 flex items-center justify-end">
                    <ArrowRight className="w-4 h-4 text-muted-foreground group-hover:text-primary transition-colors" />
                  </div>
                </Card>
              </Link>
            );
          })}
        </div>
      )}
    </div>
  );
}
