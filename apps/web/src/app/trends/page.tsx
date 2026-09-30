"use client";

import { useEffect, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  TrendingUp,
  Flame,
  Clock,
  RefreshCw,
  Sparkles,
  AlertTriangle,
  BarChart3,
} from "lucide-react";
import { trendsApi, type TrendInsights, type AgentTrendTopic } from "@/lib/api";
import Link from "next/link";

const PLATFORMS = [
  { id: "all", label: "全部", icon: BarChart3, color: "text-primary" },
  { id: "douyin", label: "抖音", icon: Flame, color: "text-black dark:text-white" },
  { id: "xiaohongshu", label: "小红书", icon: Sparkles, color: "text-red-500" },
  { id: "bilibili", label: "B站", icon: TrendingUp, color: "text-pink-400" },
  { id: "weibo", label: "微博", icon: AlertTriangle, color: "text-orange-500" },
  { id: "kuaishou", label: "快手", icon: Clock, color: "text-orange-400" },
];

const CATEGORIES = ["全部", "娱乐", "科技", "美食", "时尚", "美妆", "3C", "知识", "生活", "旅游"];

export default function TrendsPage() {
  const [activePlatform, setActivePlatform] = useState("all");
  const [activeCategory, setActiveCategory] = useState("全部");
  const [data, setData] = useState<TrendInsights | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadData = async (platform?: string, category?: string) => {
    setLoading(true);
    setError(null);
    try {
      const result = await trendsApi.getInsights(
        platform === "all" ? undefined : platform,
        category === "全部" ? undefined : category
      );
      setData(result);
    } catch (error) {
      setData(null);
      setError(error instanceof Error ? error.message : "热点加载失败，请稍后重试");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const platform = params.get("platform");
    const category = params.get("category");
    if (platform && PLATFORMS.some((item) => item.id === platform)) setActivePlatform(platform);
    if (category && CATEGORIES.includes(category)) setActiveCategory(category);
  }, []);

  useEffect(() => {
    loadData(activePlatform, activeCategory);
  }, [activePlatform, activeCategory]);

  const handleRefresh = async () => {
    setRefreshing(true);
    try {
      await trendsApi.crawlNow(activePlatform === "all" ? undefined : activePlatform);
      await new Promise((r) => setTimeout(r, 2000));
      await loadData(activePlatform, activeCategory);
    } catch (error) {
      setError(error instanceof Error ? error.message : "热点刷新失败，请稍后重试");
    } finally {
      setRefreshing(false);
    }
  };

  const filteredTrends = data?.trends || [];

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold flex items-center gap-2">
            <TrendingUp className="w-6 h-6 text-primary" />
            热点灵感中心
          </h1>
          <p className="text-sm text-muted-foreground mt-1">
            实时追踪5大平台热点趋势，AI分析生命周期，帮你抢占流量窗口
          </p>
        </div>
        <Button onClick={handleRefresh} disabled={refreshing} size="sm" variant="secondary">
          <RefreshCw className={`w-4 h-4 mr-2 ${refreshing ? "animate-spin" : ""}`} />
          {refreshing ? "刷新中..." : "立即刷新"}
        </Button>
      </div>

      {error && (
        <Card className="border-destructive/40 bg-destructive/5">
          <CardContent className="p-4 text-sm text-destructive" role="alert">{error}</CardContent>
        </Card>
      )}

      {data?.timed_out && (
        <Card className="border-amber-500/40 bg-amber-50/70 dark:bg-amber-950/20">
          <CardContent className="p-4 text-sm text-amber-800 dark:text-amber-200" role="status">
            热点平台响应超时，暂时无法获取实时榜单。请稍后重试；已返回的数据仍可查看。
          </CardContent>
        </Card>
      )}
      {data?.errors && Object.keys(data.errors).length > 0 && !data.timed_out && (
        <Card className="border-amber-500/40 bg-amber-50/70 dark:bg-amber-950/20">
          <CardContent className="p-4 text-sm text-amber-800 dark:text-amber-200" role="status">
            部分平台暂不可用（{Object.keys(data.errors).join("、")}），以下展示其余平台已获取的数据。
          </CardContent>
        </Card>
      )}

      {/* Summary Banner */}
      {data?.summary && (
        <Card className="bg-blue-50 border-blue-100">
          <CardContent className="p-4">
            <p className="text-sm flex items-start gap-2">
              <Sparkles className="w-4 h-4 text-primary mt-0.5 flex-shrink-0" />
              <span>{data.summary}</span>
            </p>
          </CardContent>
        </Card>
      )}

      {/* Rising Alerts */}
      {data?.rising_alerts && data.rising_alerts.length > 0 && (
        <div className="space-y-2">
          <h2 className="text-sm font-semibold text-destructive flex items-center gap-2">
            <Flame className="w-4 h-4" /> 上升期热点预警
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
            {data.rising_alerts.slice(0, 6).map((alert, i) => (
              <Card key={i} className="border-l-4 border-l-red-500 hover:shadow-md transition-shadow">
                <CardContent className="p-3">
                  <div className="flex items-start justify-between">
                    <div className="flex-1 min-w-0">
                      <p className="font-medium text-sm truncate">{alert.title}</p>
                      <div className="flex items-center gap-2 mt-1">
                        <Badge variant="default" className="text-xs">
                          {alert.platform}
                        </Badge>
                        {alert.category && (
                          <Badge variant="default" className="text-xs">
                            {alert.category}
                          </Badge>
                        )}
                      </div>
                    </div>
                    <Badge
                      variant={alert.urgency === "high" ? "danger" : "default"}
                      className="text-xs ml-2"
                    >
                      +{Math.round(alert.growth_rate * 100)}%
                    </Badge>
                  </div>
                  <p className="text-xs text-muted-foreground mt-2">{alert.recommended_action}</p>
                </CardContent>
              </Card>
            ))}
          </div>
        </div>
      )}

      {/* Platform Tabs */}
      <div className="flex items-center gap-2 overflow-x-auto pb-2">
        {PLATFORMS.map((p) => {
          const Icon = p.icon;
          const isActive = activePlatform === p.id;
          return (
            <button
              key={p.id}
              onClick={() => setActivePlatform(p.id)}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-full text-sm font-medium transition-colors whitespace-nowrap ${
                isActive
                  ? "bg-primary text-primary-foreground"
                  : "bg-muted text-muted-foreground hover:bg-muted/80"
              }`}
            >
              <Icon className={`w-3.5 h-3.5 ${isActive ? "" : p.color}`} />
              {p.label}
            </button>
          );
        })}
      </div>

      {/* Category Filter */}
      <div className="flex items-center gap-1.5 flex-wrap">
        {CATEGORIES.map((cat) => (
          <button
            key={cat}
            onClick={() => setActiveCategory(cat)}
            className={`px-2.5 py-1 rounded-md text-xs transition-colors ${
              activeCategory === cat
                ? "bg-primary/10 text-primary font-medium"
                : "text-muted-foreground hover:text-foreground hover:bg-muted"
            }`}
          >
            {cat}
          </button>
        ))}
      </div>

      {/* Quick Actions */}
      <div className="flex gap-3">
        <Link href="/topics">
          <Button size="sm" className="gap-2">
            <Sparkles className="w-4 h-4" />
            AI智能选题
          </Button>
        </Link>
        <Link href="/viral">
          <Button size="sm" variant="secondary" className="gap-2">
            <BarChart3 className="w-4 h-4" />
            爆款拆解库
          </Button>
        </Link>
      </div>

      {/* Hot Topics List */}
      <div className="space-y-2">
        <div className="flex items-center justify-between">
          <h2 className="text-sm font-semibold">热榜话题 ({filteredTrends.length})</h2>
        </div>

        {loading ? (
          <div className="grid gap-2">
            {[1, 2, 3, 4, 5, 6].map((i) => (
              <Card key={i} className="animate-pulse">
                <CardContent className="p-4">
                  <div className="h-4 bg-muted rounded w-3/4 mb-2" />
                  <div className="h-3 bg-muted rounded w-1/2" />
                </CardContent>
              </Card>
            ))}
          </div>
        ) : filteredTrends.length === 0 ? (
          <Card>
            <CardContent className="p-8 text-center text-muted-foreground">
              暂无热点数据
            </CardContent>
          </Card>
        ) : (
          <div className="grid gap-2">
            {filteredTrends.map((topic, index) => (
              <TrendTopicCard key={`${topic.platform}:${topic.topic_id || topic.title || index}`} topic={topic} rank={index + 1} />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

function TrendTopicCard({ topic, rank }: { topic: AgentTrendTopic; rank: number }) {
  const lifecycleStage = typeof topic.extra?.lifecycle_stage === "string"
    ? topic.extra.lifecycle_stage
    : undefined;
  const lifecycleLabels: Record<string, string> = {
    emerging: "萌芽期",
    rising: "上升期",
    peak: "峰值期",
    declining: "下降期",
    stale: "过时",
  };
  const isHot = lifecycleStage === "rising" || (topic.hot_value_growth ?? 0) > 0.5;
  const growthPercent = Math.round((topic.hot_value_growth ?? 0) * 100);

  return (
    <Card className="hover:shadow-md transition-shadow cursor-pointer group">
      <CardContent className="p-4 flex items-center gap-4">
        {/* Rank */}
        <div
          className={`w-8 h-8 rounded-lg flex items-center justify-center text-sm font-bold flex-shrink-0 ${
            rank <= 3
              ? "bg-[#FF9500] text-white"
              : "bg-muted text-muted-foreground"
          }`}
        >
          {rank}
        </div>

        {/* Content */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <p className="font-medium text-sm truncate group-hover:text-primary transition-colors">
              {topic.title}
            </p>
            {isHot && <Flame className="w-3.5 h-3.5 text-red-500 flex-shrink-0" />}
          </div>
          <div className="flex items-center gap-2 mt-1 flex-wrap">
            <Badge variant="default" className="text-xs">
              {topic.platform}
            </Badge>
            {topic.category && (
              <span className="text-xs text-muted-foreground">{topic.category}</span>
            )}
            {topic.hot_value && (
              <span className="text-xs text-muted-foreground">
                热度 {(topic.hot_value / 10000).toFixed(1)}万
              </span>
            )}
          </div>
        </div>

        {/* Growth indicator */}
        <div className="text-right flex-shrink-0">
          {topic.hot_value_growth != null && (
            <div
              className={`text-sm font-semibold flex items-center gap-0.5 ${
                growthPercent >= 0 ? "text-red-500" : "text-green-500"
              }`}
            >
              <TrendingUp
                className={`w-3.5 h-3.5 ${growthPercent < 0 ? "rotate-180" : ""}`}
              />
              {growthPercent >= 0 ? "+" : ""}
              {growthPercent}%
            </div>
          )}

          {lifecycleStage && lifecycleLabels[lifecycleStage] && (
            <Badge variant="default" className="text-xs mt-1">
              {lifecycleLabels[lifecycleStage]}
            </Badge>
          )}

        </div>
      </CardContent>
    </Card>
  );
}
