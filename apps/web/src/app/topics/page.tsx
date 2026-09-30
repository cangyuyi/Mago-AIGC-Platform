"use client";

import { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle, } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import {
  Sparkles,
  Lightbulb,
  Zap,
  Target,
  TrendingUp,
  Clock,
  Film,
  AlertCircle,
  Wand2,
  RefreshCw,
  Rocket,
  ChevronRight,
  Loader2,
  Plus,
} from "lucide-react";
import { topicApi, type TopicCard } from "@/lib/api";

const CATEGORIES = [
  { id: "美妆", icon: "💄", desc: "妆容/护肤/测评" },
  { id: "美食", icon: "🍜", desc: "教程/探店/开箱" },
  { id: "时尚", icon: "👗", desc: "穿搭/单品/风格" },
  { id: "3C", icon: "📱", desc: "数码/测评/技巧" },
  { id: "剧情", icon: "🎬", desc: "情感/反转/故事" },
  { id: "知识", icon: "📚", desc: "科普/干货/冷知识" },
  { id: "生活", icon: "🏠", desc: "好物/技巧/日常" },
  { id: "旅游", icon: "✈️", desc: "攻略/景点/旅行" },
];

const PLATFORMS = [
  { id: "douyin", label: "抖音" },
  { id: "xiaohongshu", label: "小红书" },
  { id: "bilibili", label: "B站" },
  { id: "kuaishou", label: "快手" },
];

export default function TopicsPage() {
  const [selectedCategory, setSelectedCategory] = useState<string | null>(null);
  const [selectedPlatform, setSelectedPlatform] = useState<string | null>(null);
  const [keywords, setKeywords] = useState<string[]>([]);
  const [keywordInput, setKeywordInput] = useState("");
  const [referenceUrl, setReferenceUrl] = useState("");
  const [generating, setGenerating] = useState(false);
  const [topics, setTopics] = useState<TopicCard[]>([]);
  const [summary, setSummary] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const addKeyword = () => {
    if (keywordInput.trim() && !keywords.includes(keywordInput.trim())) {
      setKeywords([...keywords, keywordInput.trim()]);
      setKeywordInput("");
    }
  };

  const removeKeyword = (k: string) => {
    setKeywords(keywords.filter((x) => x !== k));
  };

  const handleGenerate = async () => {
    setGenerating(true);
    setError(null);
    try {
      const result = await topicApi.generate({
        category: selectedCategory || undefined,
        keywords: keywords.length > 0 ? keywords : undefined,
        reference_video_urls: referenceUrl ? [referenceUrl] : undefined,
        target_platform: selectedPlatform || undefined,
        count: 15,
      });
      setTopics(result.topics);
      setSummary(result.trend_summary || null);
    } catch (error) {
      console.error("Failed to generate topics:", error);
      setTopics([]);
      setSummary(null);
      setError(error instanceof Error ? error.message : "选题生成失败，请稍后重试");
    } finally {
      setGenerating(false);
    }
  };

  const canGenerate = selectedCategory || keywords.length > 0;

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold flex items-center gap-2">
          <Lightbulb className="w-6 h-6 text-amber-500" />
          AI智能选题
        </h1>
        <p className="text-sm text-muted-foreground mt-1">
          基于实时热点 + 爆款公式 + AI创意，为没有灵感的你找到创作方向
        </p>
      </div>

      {error && (
        <Card className="border-destructive/50 bg-destructive/5">
          <CardContent className="p-4 text-sm text-destructive">{error}</CardContent>
        </Card>
      )}

      {/* Step 1: Category */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base flex items-center gap-2">
            <span className="w-6 h-6 rounded-full bg-primary text-primary-foreground text-xs flex items-center justify-center">1</span>
            选择创作领域
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            {CATEGORIES.map((cat) => (
              <button
                key={cat.id}
                onClick={() => setSelectedCategory(selectedCategory === cat.id ? null : cat.id)}
                className={`p-4 rounded-xl border-2 transition-all text-left ${
                  selectedCategory === cat.id
                    ? "border-primary bg-primary/5 shadow-md"
                    : "border-border hover:border-primary/30 hover:bg-muted/50"
                }`}
              >
                <div className="text-2xl mb-1">{cat.icon}</div>
                <p className="font-medium text-sm">{cat.id}</p>
                <p className="text-xs text-muted-foreground mt-0.5">{cat.desc}</p>
              </button>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Step 2: Keywords & Preferences */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base flex items-center gap-2">
            <span className="w-6 h-6 rounded-full bg-primary text-primary-foreground text-xs flex items-center justify-center">2</span>
            添加关键词（可选）
          </CardTitle>
          <p className="text-sm text-muted-foreground">输入你想结合的关键词，或粘贴参考视频链接</p>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex gap-2">
            <Input
              placeholder="输入关键词，按回车添加（如：秋季、口红、平价）"
              value={keywordInput}
              onChange={(e) => setKeywordInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter") {
                  e.preventDefault();
                  addKeyword();
                }
              }}
              className="flex-1"
            />
            <Button variant="secondary" onClick={addKeyword} size="sm" className="w-8 h-8 p-0">
              <Plus className="w-4 h-4" />
            </Button>
          </div>
          {keywords.length > 0 && (
            <div className="flex gap-2 flex-wrap">
              {keywords.map((k) => (
                <Badge key={k} variant="default" className="gap-1 cursor-pointer" onClick={() => removeKeyword(k)}>
                  {k} <span className="text-xs opacity-60">×</span>
                </Badge>
              ))}
            </div>
          )}

          <div>
            <p className="text-xs text-muted-foreground mb-2">目标平台</p>
            <div className="flex gap-2 flex-wrap">
              {PLATFORMS.map((p) => (
                <button
                  key={p.id}
                  onClick={() => setSelectedPlatform(selectedPlatform === p.id ? null : p.id)}
                  className={`px-3 py-1.5 rounded-full text-xs font-medium transition-colors ${
                    selectedPlatform === p.id
                      ? "bg-primary text-primary-foreground"
                      : "bg-muted text-muted-foreground hover:bg-muted/80"
                  }`}
                >
                  {p.label}
                </button>
              ))}
            </div>
          </div>

          <div>
            <p className="text-xs text-muted-foreground mb-2">参考视频URL（可选，AI会分析其结构）</p>
            <Input
              placeholder="粘贴一个你想模仿的爆款视频链接"
              value={referenceUrl}
              onChange={(e) => setReferenceUrl(e.target.value)}
            />
          </div>
        </CardContent>
      </Card>

      {/* Generate Button */}
      <div className="flex justify-center">
        <Button
          size="lg"
          onClick={handleGenerate}
          disabled={!canGenerate || generating}
          className="gap-2 px-8"
        >
          {generating ? (
            <>
              <Loader2 className="w-5 h-5 animate-spin" />
              AI创意生成中...（通常5-10秒）
            </>
          ) : (
            <>
              <Wand2 className="w-5 h-5" />
              帮我找选题灵感
              <ChevronRight className="w-4 h-4" />
            </>
          )}
        </Button>
      </div>

      {/* Results */}
      {topics.length > 0 && (
        <div className="space-y-4">
          {/* Trend Summary */}
          {summary && (
            <Card className="bg-orange-50 border-orange-100">
              <CardContent className="p-4">
                <p className="text-sm flex items-start gap-2">
                  <TrendingUp className="w-4 h-4 text-amber-600 mt-0.5 flex-shrink-0" />
                  <span>{summary}</span>
                </p>
              </CardContent>
            </Card>
          )}

          <div className="flex items-center justify-between">
            <h2 className="text-lg font-semibold flex items-center gap-2">
              <Rocket className="w-5 h-5 text-primary" />
              为你生成的{topics.length}个选题方向
            </h2>
            <Button variant="ghost" size="sm" onClick={handleGenerate} disabled={generating} className="gap-2">
              <RefreshCw className={`w-4 h-4 ${generating ? "animate-spin" : ""}`} />
              换一批
            </Button>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {topics.map((topic, i) => (
              <TopicCardItem key={i} topic={topic} rank={i + 1} />
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function TopicCardItem({ topic, rank }: { topic: TopicCard; rank: number }) {
  const [expanded, setExpanded] = useState(false);

  const scoreColor =
    topic.estimated_viral_potential >= 80
      ? "text-red-500 bg-red-500/10"
      : topic.estimated_viral_potential >= 60
      ? "text-orange-500 bg-orange-500/10"
      : "text-blue-500 bg-blue-500/10";

  const hookTypeLabels: Record<string, string> = {
    question: "提问式", shock: "震惊式", curiosity: "好奇式",
    number: "数字式", contrast: "对比式", pain_point: "痛点式",
    demo: "演示式", story: "故事式",
  };

  return (
    <Card className="hover:shadow-lg transition-all group">
      <CardContent className="p-5">
        <div className="flex items-start justify-between gap-3">
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 mb-2">
              <span className={`text-xs font-bold px-2 py-0.5 rounded-full ${scoreColor}`}>
                {topic.estimated_viral_potential.toFixed(0)}分
              </span>
              {topic.supporting_trends.length > 0 && (
                <Badge variant="default" className="text-xs text-amber-600 border-amber-200">
                  <TrendingUp className="w-3 h-3 mr-0.5" /> 热点加持
                </Badge>
              )}
              {rank <= 3 && (
                <Badge className="bg-[#FF9500] text-white text-xs border-0">
                  TOP{rank}
                </Badge>
              )}
            </div>
            <h3 className="font-semibold text-sm leading-snug group-hover:text-primary transition-colors">
              {topic.title}
            </h3>
          </div>
        </div>

        {/* Hook */}
        <div className="mt-3 bg-muted/50 rounded-lg p-3">
          <div className="flex items-center gap-1.5 mb-1">
            <Zap className="w-3 h-3 text-amber-500" />
            <span className="text-xs font-medium text-amber-600">开头钩子建议</span>
          </div>
          <p className="text-sm">{topic.hook_suggestion}</p>
        </div>

        {/* Expanded content */}
        {expanded && (
          <div className="mt-3 space-y-3 animate-in fade-in duration-200">
            <div>
              <p className="text-xs font-medium flex items-center gap-1 text-muted-foreground mb-1">
                <Target className="w-3 h-3" /> 内容方向
              </p>
              <p className="text-sm">{topic.content_direction}</p>
            </div>

            {topic.script_outline && (
              <div>
                <p className="text-xs font-medium flex items-center gap-1 text-muted-foreground mb-1">
                  <Film className="w-3 h-3" /> 脚本大纲
                </p>
                <p className="text-sm">{topic.script_outline}</p>
              </div>
            )}

            {topic.visual_concept && (
              <div>
                <p className="text-xs font-medium flex items-center gap-1 text-muted-foreground mb-1">
                  <Sparkles className="w-3 h-3" /> 视觉概念
                </p>
                <p className="text-sm">{topic.visual_concept}</p>
              </div>
            )}

            <div className="grid grid-cols-2 gap-3">
              <div>
                <p className="text-xs font-medium flex items-center gap-1 text-muted-foreground mb-1">
                  <Clock className="w-3 h-3" /> 建议时长
                </p>
                <p className="text-sm">{topic.target_duration}</p>
              </div>
              <div>
                <p className="text-xs font-medium text-muted-foreground mb-1">平台</p>
                <div className="flex gap-1 flex-wrap">
                  {topic.target_platform.map((p) => (
                    <Badge key={p} variant="default" className="text-xs">{p}</Badge>
                  ))}
                </div>
              </div>
            </div>

            <div>
              <p className="text-xs font-medium text-green-600 mb-1">✅ 爆点</p>
              <div className="flex gap-1 flex-wrap">
                {topic.key_selling_points.map((p, i) => (
                  <span key={i} className="text-xs text-green-700 bg-green-50 dark:bg-green-950/30 px-2 py-0.5 rounded">
                    {p}
                  </span>
                ))}
              </div>
            </div>

            {topic.risk_factors.length > 0 && (
              <div>
                <p className="text-xs font-medium text-amber-600 mb-1 flex items-center gap-1">
                  <AlertCircle className="w-3 h-3" /> 风险提示
                </p>
                <div className="flex gap-1 flex-wrap">
                  {topic.risk_factors.map((r, i) => (
                    <span key={i} className="text-xs text-amber-700 bg-amber-50 dark:bg-amber-950/30 px-2 py-0.5 rounded">
                      {r}
                    </span>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        <div className="flex items-center justify-between mt-3 pt-3 border-t">
          <div className="flex gap-1 flex-wrap">
            {topic.tags.slice(0, 4).map((t) => (
              <span key={t} className="text-xs text-muted-foreground">#{t}</span>
            ))}
          </div>
          <div className="flex gap-2">
            <button
              onClick={() => setExpanded(!expanded)}
              className="text-xs text-muted-foreground hover:text-primary transition-colors"
            >
              {expanded ? "收起" : "展开详情"}
            </button>
            <Button size="sm" variant="secondary" className="text-xs h-7 gap-1">
              <Plus className="w-3 h-3" /> 用此创建项目
            </Button>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

