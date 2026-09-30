/**
 * Core API client for backend calls.
 */
import { apiFetch } from "./auth";
import type { CreateCharacterRequest, CreateProjectRequest, Character, Project, Prompt, PromptPackage, UpdateProjectRequest } from "@mago/shared-types";

export type { Character, Project, Prompt, PromptPackage } from "@mago/shared-types";

export interface PaginatedResult<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
}

export const charactersApi = {
  list: (page = 1, pageSize = 20) =>
    apiFetch<PaginatedResult<Character>>(`/api/v1/characters?page=${page}&page_size=${pageSize}`),
  create: (data: CreateCharacterRequest) =>
    apiFetch<Character>("/api/v1/characters", { method: "POST", body: JSON.stringify(data) }),
  delete: (id: string) => apiFetch<void>(`/api/v1/characters/${id}`, { method: "DELETE" }),
};

export const projectsApi = {
  list: (page = 1, pageSize = 20) =>
    apiFetch<PaginatedResult<Project>>(`/api/v1/projects?page=${page}&page_size=${pageSize}`),

  create: (data: CreateProjectRequest) =>
    apiFetch<Project>("/api/v1/projects", { method: "POST", body: JSON.stringify(data) }),

  get: (id: string) => apiFetch<Project>(`/api/v1/projects/${id}`),

  update: (id: string, data: UpdateProjectRequest) =>
    apiFetch<Project>(`/api/v1/projects/${id}`, { method: "PUT", body: JSON.stringify(data) }),

  delete: (id: string) => apiFetch<void>(`/api/v1/projects/${id}`, { method: "DELETE" }),
};

export const promptsApi = {
  listPackages: (projectId: string) => apiFetch<PromptPackage[]>(`/api/v1/prompt-packages?project_id=${encodeURIComponent(projectId)}`),
  getPackage: (id: string) => apiFetch<{ package: PromptPackage; prompts: Prompt[] }>(`/api/v1/prompt-packages/${id}`),
};

export const authApi = {
  login: (email: string, password: string) =>
    apiFetch<{ access_token: string; refresh_token: string; user: { id: string; email: string; name: string; role: string } }>(
      "/api/v1/auth/login",
      { method: "POST", body: JSON.stringify({ email, password }) }
    ),
  register: (email: string, password: string, name: string) =>
    apiFetch<{ access_token: string; refresh_token: string; user: { id: string; email: string; name: string; role: string } }>("/api/v1/auth/register", {
      method: "POST",
      body: JSON.stringify({ email, password, name }),
    }),
  me: () => apiFetch("/api/v1/auth/me"),
};

// ============ Trend Intelligence APIs ============

/** Trend DTO returned by the Python Agent insights endpoint (not the Go DB entity). */
export interface AgentTrendTopic {
  platform: string;
  topic_id?: string | null;
  title: string;
  category?: string | null;
  hot_value?: number | null;
  hot_value_growth?: number | null;
  rank_position?: number | null;
  cover_url?: string | null;
  url?: string | null;
  tags: string[];
  extra: Record<string, unknown>;
}

export interface ViralVideo {
  id: string;
  platform: string;
  video_id: string;
  url: string;
  author_name?: string;
  title?: string;
  description?: string;
  tags: string[];
  category?: string;
  duration?: number;
  width?: number;
  height?: number;
  aspect_ratio?: string;
  metrics?: Record<string, unknown>;
  viral_score?: number;
  analysis_status: string;
  thumbnail_url?: string;
  bgm_bpm?: number;
  bgm_emotion?: string;
  transcript?: string;
  shot_count?: number;
  avg_shot_duration?: number;
  hook_text?: string;
  hook_type?: string;
  hook_engagement_score?: number;
  narrative_structure?: Record<string, unknown>;
  visual_language?: Record<string, unknown>;
  rhythm_analysis?: Record<string, unknown>;
  emotion_curve?: Array<Record<string, unknown>>;
  keyframe_urls?: string[];
  analyzed_at?: string;
  shots?: Array<{
    id: string;
    shot_index: number;
    start_time: number;
    end_time: number;
    duration: number;
    keyframe_url?: string;
    transcript?: string;
    visual_description?: string;
    emotion_tag?: string;
    transition_type?: string;
    motion_intensity?: number;
    onset_strength?: number;
  }>;
  analysis?: Record<string, unknown>;
}

/** Result returned by the Python Agent analysis task; distinct from the Go ViralVideo entity. */
export interface AgentViralAnalysisResult {
  video_id?: string | null;
  platform?: string | null;
  url: string;
  title?: string | null;
  description?: string | null;
  duration?: number | null;
  width?: number | null;
  height?: number | null;
  aspect_ratio?: string | null;
  transcript?: string | null;
  shots: Array<{
    shot_index: number;
    start_time: number;
    end_time: number;
    duration: number;
    keyframe_path?: string | null;
    keyframe_url?: string | null;
    transcript?: string | null;
    transcript_words: Array<Record<string, unknown>>;
    visual_description?: string | null;
    visual_tags: string[];
    camera_movement?: string | null;
    camera_angle?: string | null;
    lighting?: string | null;
    color_palette: string[];
    emotion_tag?: string | null;
    text_ocr?: string | null;
    transition_type?: string | null;
    has_face: boolean;
    face_count: number;
    motion_intensity: number;
    audio_type?: string | null;
    onset_strength: number;
  }>;
  hook?: Record<string, unknown> | null;
  narrative?: Record<string, unknown> | null;
  visual?: Record<string, unknown> | null;
  audio?: Record<string, unknown> | null;
  patterns: Array<Record<string, unknown>>;
  emotion_curve: Array<Record<string, unknown>>;
  rhythm_curve: Array<Record<string, unknown>>;
  viral_score: number;
  viral_score_breakdown: Record<string, number>;
  keyframe_paths: string[];
  summary?: string | null;
  analysis_version: string;
  analyzed_at: string;
  model_info: Record<string, unknown>;
}

export interface AnalysisTask<T> {
  id: string;
  type?: string;
  url?: string;
  status: string;
  progress: number;
  stage?: string;
  message?: string;
  error?: string;
  result?: T | null;
}

export interface TopicCard {
  title: string;
  hook_suggestion: string;
  content_direction: string;
  target_platform: string[];
  target_duration: string;
  estimated_viral_potential: number;
  supporting_trends: string[];
  reference_patterns: string[];
  key_selling_points: string[];
  risk_factors: string[];
  script_outline?: string;
  visual_concept?: string;
  tags: string[];
}

export interface TopicRecommendResponse {
  topics: TopicCard[];
  trend_summary?: string;
  model_info: Record<string, unknown>;
  generated_at: string;
}

export interface TrendInsights {
  summary: string;
  total_topics: number;
  rising_alerts: Array<{
    title: string;
    platform: string;
    category?: string;
    growth_rate: number;
    hot_value?: number;
    urgency: string;
    recommended_action: string;
  }>;
  cross_platform_trends: Array<Record<string, unknown>>;
  trends: AgentTrendTopic[];
  timed_out: boolean;
  errors: Record<string, string>;
}

export const trendsApi = {
  // Get trend insights (crawls + analysis)
  getInsights: (platform?: string, category?: string) => {
    const params = new URLSearchParams();
    if (platform) params.set("platform", platform);
    if (category) params.set("category", category);
    const qs = params.toString();
    return apiFetch<TrendInsights>(`/api/agent/trends/insights${qs ? `?${qs}` : ""}`);
  },

  // Trigger immediate crawl (admin)
  crawlNow: (platform?: string) =>
    apiFetch<{ task_id: string; status: string }>("/api/agent/trends/crawl-now", {
      method: "POST",
      body: JSON.stringify({ platform }),
    }),

  // Get task status
  getTaskStatus: (taskId: string) =>
    apiFetch<{ id: string; type: string; status: string; progress: number; result?: unknown }>(
      `/api/agent/trends/task/${taskId}`
    ),
};

export const viralApi = {
  list: (params: { platform?: string; category?: string; page?: number; pageSize?: number } = {}) => {
    const query = new URLSearchParams();
    if (params.platform) query.set("platform", params.platform);
    if (params.category) query.set("category", params.category);
    query.set("page", String(params.page ?? 1));
    query.set("page_size", String(params.pageSize ?? 20));
    return apiFetch<PaginatedResult<ViralVideo>>(`/api/v1/viral-videos?${query.toString()}`);
  },

  get: (id: string) => apiFetch<ViralVideo>(`/api/v1/viral-videos/${id}`),

  // Submit video for analysis
  analyze: (url: string, platform?: string, category?: string) =>
    apiFetch<{ task_id: string; status: string; url: string }>("/api/agent/viral-videos/analyze", {
      method: "POST",
      body: JSON.stringify({
        url,
        ...(platform ? { platform } : {}),
        ...(category ? { category } : {}),
      }),
    }),

  // Get analysis result
  getResult: (taskId: string) =>
    apiFetch<AnalysisTask<AgentViralAnalysisResult>>(
      `/api/agent/viral-videos/analyze/${taskId}`
    ),
};

export const topicApi = {
  // Generate topic recommendations
  generate: (data: {
    category?: string;
    keywords?: string[];
    reference_video_urls?: string[];
    count?: number;
    target_platform?: string;
  }) =>
    apiFetch<TopicRecommendResponse>("/api/agent/topic-recommendations/generate", {
      method: "POST",
      body: JSON.stringify(data),
    }),
};
