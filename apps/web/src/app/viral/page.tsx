"use client";

import { useCallback, useEffect, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import {
  Film,
  Search,
  ExternalLink,
  TrendingUp,
  Play,
  Sparkles,
  Loader2,
} from "lucide-react";
import Link from "next/link";
import { viralApi, type AnalysisTask, type AgentViralAnalysisResult, type ViralVideo } from "@/lib/api";

export default function ViralPage() {
  const [url, setUrl] = useState("");
  const [analyzing, setAnalyzing] = useState(false);
  const [taskId, setTaskId] = useState<string | null>(null);
  const [analysisTask, setAnalysisTask] = useState<AnalysisTask<AgentViralAnalysisResult> | null>(null);
  const [videos, setVideos] = useState<ViralVideo[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeCategory, setActiveCategory] = useState("全部");

  const categories = ["全部", "美妆", "美食", "时尚", "3C", "剧情", "知识", "生活"];
  const filteredVideos =
    activeCategory === "全部"
      ? videos
      : videos.filter((v) => v.category === activeCategory);

  const loadVideos = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await viralApi.list({
        category: activeCategory === "全部" ? undefined : activeCategory,
      });
      setVideos(result.items || []);
    } catch (e) {
      setVideos([]);
      setError(e instanceof Error ? e.message : "爆款视频加载失败，请稍后重试");
    } finally {
      setLoading(false);
    }
  }, [activeCategory]);

  useEffect(() => {
    void loadVideos();
  }, [loadVideos]);

  useEffect(() => {
    if (!taskId) return;

    let active = true;
    let timer: ReturnType<typeof setTimeout> | undefined;
    const poll = async () => {
      try {
        const task = await viralApi.getResult(taskId);
        if (!active) return;
        setAnalysisTask(task);
        if (task.status === "queued" || task.status === "running") {
          timer = setTimeout(() => void poll(), 2000);
        }
      } catch (e) {
        if (!active) return;
        setAnalysisTask((current) => current ? {
          ...current,
          error: e instanceof Error ? e.message : "分析任务状态获取失败",
        } : current);
      }
    };

    void poll();
    return () => {
      active = false;
      if (timer) clearTimeout(timer);
    };
  }, [taskId]);

  const handleAnalyze = async () => {
    if (!url.trim()) return;
    setAnalyzing(true);
    setError(null);
    try {
      const result = await viralApi.analyze(url.trim());
      setTaskId(result.task_id);
      setAnalysisTask({ id: result.task_id, status: result.status, progress: 0 });
      setUrl("");
    } catch (e) {
      setError(e instanceof Error ? e.message : "视频分析任务提交失败，请稍后重试");
    } finally {
      setAnalyzing(false);
    }
  };

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold flex items-center gap-2">
            <Film className="w-6 h-6 text-primary" />
            爆款拆解库
          </h1>
          <p className="text-sm text-muted-foreground mt-1">
            AI多模态拆解爆款视频结构，提取可复用公式
          </p>
        </div>
      </div>

      {/* URL Analysis Form */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base flex items-center gap-2">
            <Sparkles className="w-4 h-4 text-primary" />
            提交视频分析
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex gap-3">
            <Input
              placeholder="粘贴视频URL（抖音/快手/小红书/B站/YouTube...）"
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              className="flex-1"
            />
            <Button onClick={handleAnalyze} disabled={!url.trim() || analyzing}>
              {analyzing ? (
                <>
                  <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                  分析中...
                </>
              ) : (
                "开始拆解"
              )}
            </Button>
          </div>
          {analysisTask && (
            <div className="mt-3 space-y-2" aria-live="polite">
              <p className="text-xs text-muted-foreground">
                任务 {analysisTask.id} · {analysisTask.status === "queued" ? "排队中" : analysisTask.status === "running" ? `分析中 ${analysisTask.progress}%` : analysisTask.status === "completed" ? "分析完成" : analysisTask.status === "failed" ? "分析失败" : analysisTask.status}
                {analysisTask.stage ? ` · ${analysisTask.stage}` : ""}
              </p>
              {(analysisTask.status === "queued" || analysisTask.status === "running") && (
                <div className="h-1.5 rounded bg-muted overflow-hidden">
                  <div className="h-full bg-primary transition-all" style={{ width: `${Math.max(0, Math.min(100, analysisTask.progress))}%` }} />
                </div>
              )}
              {analysisTask.status === "completed" && analysisTask.result && (
                <div className="rounded-lg border p-3 text-sm">
                  <p className="font-medium">{analysisTask.result.title || "视频分析已完成"} · {analysisTask.result.viral_score}分</p>
                  {analysisTask.result.summary && <p className="mt-1 text-muted-foreground">{analysisTask.result.summary}</p>}
                  {analysisTask.result.hook && typeof analysisTask.result.hook.hook_text === "string" && (
                    <p className="mt-1 text-muted-foreground">开场钩子：{analysisTask.result.hook.hook_text}</p>
                  )}
                </div>
              )}
              {analysisTask.status === "failed" && <p className="text-xs text-destructive">{analysisTask.error || "视频分析失败"}</p>}
              {analysisTask.status !== "failed" && analysisTask.error && <p className="text-xs text-destructive">{analysisTask.error}</p>}
            </div>
          )}
        </CardContent>
      </Card>

      {error && (
        <p className="text-sm text-destructive" role="alert">{error}</p>
      )}

      {/* Category Filter */}
      <div className="flex items-center gap-1.5 flex-wrap">
        {categories.map((cat) => (
          <button
            key={cat}
            onClick={() => setActiveCategory(cat)}
            className={`px-3 py-1 rounded-full text-xs transition-colors ${
              activeCategory === cat
                ? "bg-primary text-primary-foreground"
                : "bg-muted text-muted-foreground hover:bg-muted/80"
            }`}
          >
            {cat}
          </button>
        ))}
      </div>

      {/* Video Grid */}
      {loading ? (
        <div className="py-12 text-center text-muted-foreground">加载中...</div>
      ) : filteredVideos.length === 0 ? (
        <div className="py-12 text-center text-muted-foreground">暂无已完成的爆款视频分析</div>
      ) : (
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {filteredVideos.map((video) => (
          <Link key={video.id} href={`/viral/${video.id}`}>
            <Card className="h-full hover:shadow-lg transition-shadow cursor-pointer group">
              {/* Thumbnail placeholder */}
              <div className="aspect-video bg-[#f5f5f7] relative flex items-center justify-center rounded-t-lg overflow-hidden">
                <Play className="w-10 h-10 text-muted-foreground/30 group-hover:text-primary/50 transition-colors" />
                <div className="absolute bottom-2 right-2 bg-black/60 text-white text-xs px-1.5 py-0.5 rounded">
                  {Math.floor((video.duration ?? 0) / 60)}:{String((video.duration ?? 0) % 60).padStart(2, "0")}
                </div>
                <Badge className="absolute top-2 left-2" variant="default">
                  {video.platform}
                </Badge>
              </div>
              <CardContent className="p-4">
                <p className="font-medium text-sm line-clamp-2 group-hover:text-primary transition-colors">
                  {video.title}
                </p>
                <div className="flex items-center gap-2 mt-2">
                  <Badge variant="default" className="text-xs">
                    {video.category}
                  </Badge>
                  <span className="text-xs text-muted-foreground">{video.author_name || "未知作者"}</span>
                </div>
                <div className="flex items-center justify-between mt-3">
                  <div className="flex items-center gap-1">
                    <TrendingUp className="w-3.5 h-3.5 text-red-500" />
                    <span className="text-sm font-semibold text-red-500">
                      {video.viral_score}分
                    </span>
                  </div>
                  <div className="text-xs text-muted-foreground">
                    {video.shot_count ?? 0}个镜头 · {video.bgm_bpm ?? "--"} BPM
                  </div>
                </div>
                <div className="flex gap-1 mt-2 flex-wrap">
                  {(video.tags || []).slice(0, 3).map((tag) => (
                    <span key={tag} className="text-xs text-muted-foreground">
                      #{tag}
                    </span>
                  ))}
                </div>
              </CardContent>
            </Card>
          </Link>
        ))}
      </div>
      )}
    </div>
  );
}
