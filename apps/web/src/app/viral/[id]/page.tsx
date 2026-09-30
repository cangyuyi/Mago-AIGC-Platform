"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { ArrowLeft, Camera, Clock, ExternalLink, Film, Loader2, Music, Target, TrendingUp, Zap } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { viralApi, type ViralVideo } from "@/lib/api";

function text(value: unknown, fallback = "暂无") {
  if (typeof value === "string" && value.trim()) return value;
  if (typeof value === "number") return String(value);
  return fallback;
}

function jsonText(value: unknown) {
  if (value == null) return "暂无分析数据";
  if (typeof value === "string") return value;
  try { return JSON.stringify(value, null, 2); } catch { return "暂无分析数据"; }
}

export default function ViralDetailPage() {
  const params = useParams<{ id: string }>();
  const id = Array.isArray(params.id) ? params.id[0] : params.id;
  const [video, setVideo] = useState<ViralVideo | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!id) return;
    let active = true;
    setLoading(true);
    viralApi.get(id).then((result) => {
      if (active) setVideo(result);
    }).catch((err) => {
      if (active) setError(err instanceof Error ? err.message : "爆款详情加载失败");
    }).finally(() => {
      if (active) setLoading(false);
    });
    return () => { active = false; };
  }, [id]);

  const shots = video?.shots ?? [];
  const metrics = video?.metrics ?? {};
  const analysis = video?.analysis ?? {};
  const score = video?.viral_score ?? 0;
  const duration = video?.duration ?? 0;
  const summary = {
    hook: video?.hook_text || (typeof analysis.hook_text === "string" ? analysis.hook_text : "暂无钩子文本"),
    narrative: video?.narrative_structure || analysis.narrative_structure,
    visual: video?.visual_language || analysis.visual_language,
    rhythm: video?.rhythm_analysis || analysis.rhythm_analysis,
  };

  if (loading) return <div className="py-20 text-center text-muted-foreground"><Loader2 className="w-6 h-6 animate-spin inline mr-2" />加载中...</div>;
  if (error || !video) return (
    <div className="p-6 max-w-4xl mx-auto">
      <Link href="/viral"><Button variant="ghost" size="sm"><ArrowLeft className="w-4 h-4 mr-2" />返回爆款库</Button></Link>
      <Card className="mt-6"><CardContent className="py-12 text-center text-destructive">{error || "找不到该视频"}</CardContent></Card>
    </div>
  );

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-6">
      <Link href="/viral"><Button variant="ghost" size="sm" className="gap-2"><ArrowLeft className="w-4 h-4" />返回爆款库</Button></Link>
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="space-y-4">
          <Card>
            <div className="aspect-[9/16] bg-[#1d1d1f] relative flex items-center justify-center rounded-t-lg overflow-hidden">
              {video.thumbnail_url ? (
                // Thumbnails come from third-party video platforms. Use the browser
                // loader instead of next/image so an unbounded set of platform
                // hosts does not break the page or require an unsafe wildcard
                // image remote pattern in next.config.mjs.
                // eslint-disable-next-line @next/next/no-img-element
                <img
                  src={video.thumbnail_url}
                  alt={text(video.title, "视频封面")}
                  loading="lazy"
                  decoding="async"
                  className="absolute inset-0 h-full w-full object-cover"
                />
              ) : <Film className="w-16 h-16 text-white/30" />}
              <Badge className="absolute top-3 left-3">{text(video.platform)}</Badge>
              <Badge className="absolute bottom-3 right-3 bg-red-500 text-white border-0"><TrendingUp className="w-3 h-3 mr-1" />{score.toFixed(0)}分</Badge>
            </div>
            <CardContent className="p-4">
              <h1 className="font-semibold">{text(video.title, "未命名视频")}</h1>
              <p className="text-xs text-muted-foreground mt-1">@{text(video.author_name, "未知作者")}</p>
              <div className="flex gap-2 mt-3 flex-wrap"><Badge variant="outline">{text(video.category)}</Badge><Badge variant="outline">{Math.floor(duration / 60)}:{String(Math.floor(duration % 60)).padStart(2, "0")}</Badge><Badge variant="outline">{shots.length || video.shot_count || 0}个镜头</Badge></div>
              <a href={video.url} target="_blank" rel="noreferrer"><Button variant="outline" size="sm" className="mt-4 gap-2">打开原视频<ExternalLink className="w-3 h-3" /></Button></a>
            </CardContent>
          </Card>
          <Card><CardHeader><CardTitle className="text-sm">关键指标</CardTitle></CardHeader><CardContent className="grid grid-cols-2 gap-4 text-sm">
            <Metric icon={<Target className="w-4 h-4" />} label="爆款评分" value={`${score.toFixed(0)}`} />
            <Metric icon={<Clock className="w-4 h-4" />} label="平均镜头" value={`${video.avg_shot_duration?.toFixed(1) ?? "--"}s`} />
            <Metric icon={<Music className="w-4 h-4" />} label="BGM BPM" value={text(video.bgm_bpm, "--")} />
            <Metric icon={<Zap className="w-4 h-4" />} label="分析状态" value={text(video.analysis_status)} />
          </CardContent></Card>
        </div>

        <div className="lg:col-span-2 space-y-4">
          <Card><CardHeader><CardTitle className="text-base flex items-center gap-2"><Zap className="w-4 h-4 text-primary" />开头钩子</CardTitle></CardHeader><CardContent className="space-y-3"><p className="text-sm">{text(summary.hook)}</p><div className="flex gap-2"><Badge variant="outline">类型：{text(video.hook_type)}</Badge><Badge variant="outline">吸引力：{video.hook_engagement_score != null ? `${(video.hook_engagement_score * 100).toFixed(0)}%` : "暂无"}</Badge></div></CardContent></Card>
          <DataCard title="叙事结构" icon={<Film className="w-4 h-4" />} value={summary.narrative} />
          <DataCard title="视觉语言" icon={<Camera className="w-4 h-4" />} value={summary.visual} />
          <DataCard title="节奏与音频" icon={<Music className="w-4 h-4" />} value={summary.rhythm} />
          {video.transcript && <Card><CardHeader><CardTitle className="text-base">转写文本</CardTitle></CardHeader><CardContent><p className="text-sm whitespace-pre-wrap leading-6">{video.transcript}</p></CardContent></Card>}
          <Card><CardHeader><CardTitle className="text-base">镜头时间线（{shots.length} 个）</CardTitle></CardHeader><CardContent>{shots.length === 0 ? <p className="text-sm text-muted-foreground">后端尚未返回镜头拆解。</p> : <div className="space-y-2 max-h-[28rem] overflow-y-auto">{shots.map((shot) => <div key={shot.id} className="flex items-center gap-3 p-2 rounded-lg hover:bg-muted"><div className="w-14 h-9 bg-muted rounded flex items-center justify-center"><Camera className="w-4 h-4 text-muted-foreground" /></div><div className="flex-1 min-w-0"><p className="text-xs font-medium">镜头 {(shot.shot_index ?? 0) + 1} · {shot.duration?.toFixed(1) ?? "--"}s</p><p className="text-xs text-muted-foreground truncate">{text(shot.transcript || shot.visual_description, "无描述")}</p></div><Badge variant="outline" className="text-xs">{text(shot.emotion_tag, "未标注")}</Badge></div>)}</div>}</CardContent></Card>
          <Card><CardHeader><CardTitle className="text-base">原始分析数据</CardTitle></CardHeader><CardContent><pre className="text-xs bg-muted/50 rounded-lg p-3 overflow-auto max-h-80">{jsonText({ metrics, analysis })}</pre></CardContent></Card>
        </div>
      </div>
    </div>
  );
}

function Metric({ icon, label, value }: { icon: React.ReactNode; label: string; value: string }) {
  return <div><div className="flex items-center gap-1 text-muted-foreground">{icon}<span className="text-xs">{label}</span></div><p className="font-semibold mt-1">{value}</p></div>;
}

function DataCard({ title, icon, value }: { title: string; icon: React.ReactNode; value: unknown }) {
  return <Card><CardHeader><CardTitle className="text-base flex items-center gap-2">{icon}{title}</CardTitle></CardHeader><CardContent><pre className="text-xs bg-muted/50 rounded-lg p-3 overflow-auto max-h-56 whitespace-pre-wrap">{jsonText(value)}</pre></CardContent></Card>;
}
