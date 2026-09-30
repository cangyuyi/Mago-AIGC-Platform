const TOKEN_KEY = "mago_access_token";
const REFRESH_KEY = "mago_refresh_token";
const USER_KEY = "mago_user";
const DEMO_PROJECTS_KEY = "mago_demo_projects";
const DEMO_CHARACTERS_KEY = "mago_demo_characters";

interface User {
  id: string;
  email: string;
  name: string;
  avatar_url?: string;
  role?: string;
}

export function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(TOKEN_KEY);
}

export function setToken(token: string): void {
  if (typeof window === "undefined") return;
  localStorage.setItem(TOKEN_KEY, token);
}

export function setRefreshToken(token: string): void {
  if (typeof window === "undefined") return;
  localStorage.setItem(REFRESH_KEY, token);
}

export function getRefreshToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(REFRESH_KEY);
}

export function getUser(): User | null {
  if (typeof window === "undefined") return null;
  const raw = localStorage.getItem(USER_KEY);
  if (!raw) return null;
  try {
    return JSON.parse(raw);
  } catch {
    return null;
  }
}

export function setUser(user: Partial<User> & {id: string; email: string; name: string}): void {
  if (typeof window === "undefined") return;
  const fullUser: User = { role: "user", ...user };
  localStorage.setItem(USER_KEY, JSON.stringify(fullUser));
}

export function clearAuth(): void {
  if (typeof window === "undefined") return;
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(REFRESH_KEY);
  localStorage.removeItem(USER_KEY);
}

export function isAuthenticated(): boolean {
  return !!getToken();
}

/** Demo mode is explicit so real API failures are never silently hidden. */
export function isDemoMode(): boolean {
  return process.env.NEXT_PUBLIC_DEMO_MODE === "true" || !!getToken()?.startsWith("demo_token_");
}

function getErrorMessage(data: unknown, fallback: string): string {
  if (typeof data === "object" && data !== null) {
    const value = data as Record<string, unknown>;
    for (const key of ["message", "detail", "error"]) {
      if (typeof value[key] === "string" && value[key]) return value[key] as string;
    }
  }
  return fallback;
}

let refreshPromise: Promise<string | null> | null = null;

function isAuthEndpoint(url: string): boolean {
  return /\/api\/v1\/auth\/(login|register|refresh)$/.test(url);
}

async function refreshAccessToken(): Promise<string | null> {
  const refreshToken = getRefreshToken();
  if (!refreshToken) return null;
  if (!refreshPromise) {
    refreshPromise = (async () => {
      try {
        const response = await fetch("/api/v1/auth/refresh", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ refresh_token: refreshToken }),
        });
        if (!response.ok) return null;
        const payload = (await response.json()) as { data?: { access_token?: string; refresh_token?: string }; access_token?: string; refresh_token?: string };
        const data = payload.data ?? payload;
        if (!data.access_token) return null;
        setToken(data.access_token);
        if (data.refresh_token) setRefreshToken(data.refresh_token);
        return data.access_token;
      } catch {
        return null;
      } finally {
        refreshPromise = null;
      }
    })();
  }
  return refreshPromise;
}

function requestHeaders(options: RequestInit, token: string | null): Headers {
  const headers = new Headers(options.headers);
  if (!headers.has("Content-Type") && options.body) headers.set("Content-Type", "application/json");
  if (token) headers.set("Authorization", `Bearer ${token}`);
  return headers;
}

/** Fetch an API response, retrying once with a refreshed access token after a 401. */
export async function fetchWithAuth(url: string, options: RequestInit = {}): Promise<Response> {
  if (isDemoMode() && url === "/api/agent/run") return createDemoAgentResponse(options);

  let token = getToken();
  let response = await fetch(url, { ...options, headers: requestHeaders(options, token) });
  if (response.status !== 401 || isAuthEndpoint(url)) return response;

  const refreshed = await refreshAccessToken();
  if (!refreshed) {
    clearAuth();
    if (typeof window !== "undefined" && window.location.pathname !== "/login") {
      window.location.href = "/login";
    }
    return response;
  }
  token = refreshed;
  return fetch(url, { ...options, headers: requestHeaders(options, token) });
}

export async function apiFetch<T = unknown>(url: string, options: RequestInit = {}): Promise<T> {
  // Demo mode is opt-in: use a demo token or explicitly enable it. Real API
  // failures must remain visible instead of silently returning fake data.
  if (isDemoMode()) return getMockData<T>(url, options);

  const res = await fetchWithAuth(url, options);
  if (res.status === 401) throw new Error("登录已过期，请重新登录");

  const text = await res.text();
  let data: unknown = undefined;
  if (text) {
    try {
      data = JSON.parse(text);
    } catch {
      if (!res.ok) throw new Error(`请求失败（HTTP ${res.status}）`);
      throw new Error("服务端返回了无效数据");
    }
  }
  if (!res.ok) throw new Error(getErrorMessage(data, `请求失败（HTTP ${res.status}）`));
  if (typeof data === "object" && data !== null && "code" in data && (data as {code?: unknown}).code !== 0) {
    throw new Error(getErrorMessage(data, "请求失败"));
  }
  if (!text) return undefined as T;
  return (typeof data === "object" && data !== null && "data" in data ? (data as {data?: unknown}).data : data) as T;
}

function readJsonBody(options: RequestInit): Record<string, unknown> {
  if (typeof options.body !== "string") return {};
  try {
    const value: unknown = JSON.parse(options.body);
    return typeof value === "object" && value !== null ? value as Record<string, unknown> : {};
  } catch {
    return {};
  }
}

function demoNow(offsetDays = 0): string {
  return new Date(Date.now() - offsetDays * 86400000).toISOString();
}

function readDemoList<T>(key: string, fallback: T[]): T[] {
  if (typeof window === "undefined") return fallback;
  try {
    const value = JSON.parse(localStorage.getItem(key) || "null");
    return Array.isArray(value) ? value as T[] : fallback;
  } catch {
    return fallback;
  }
}

function writeDemoList<T>(key: string, value: T[]): void {
  if (typeof window !== "undefined") localStorage.setItem(key, JSON.stringify(value));
}

function demoProjects() {
  return readDemoList(DEMO_PROJECTS_KEY, [
    { id: "demo1", name: "美妆新品带货短视频", description: "夏季新品口红推广视频", status: "draft", aspect_ratio: "9:16", created_at: demoNow(), updated_at: demoNow() },
    { id: "demo2", name: "数码产品开箱测评", description: "新款手机开箱测评", status: "draft", aspect_ratio: "9:16", created_at: demoNow(1), updated_at: demoNow(1) },
    { id: "demo3", name: "美食探店 vlog", description: "网红咖啡店探店", status: "draft", aspect_ratio: "9:16", created_at: demoNow(2), updated_at: demoNow(2) },
  ]);
}

function demoCharacters() {
  return readDemoList(DEMO_CHARACTERS_KEY, [
    { id: "demo-character-1", owner_id: "demo", name: "小美", description: "自然、亲切的美妆创作者", gender: "female", age_appearance: "young_adult", personality_vibe: "清爽亲和", prompt_fragment: "young Chinese woman, natural makeup, friendly smile", negative_fragment: "blurry, deformed hands", tags: ["美妆", "生活方式"], is_preset: true, created_at: demoNow(4), updated_at: demoNow(4) },
  ]);
}

function demoTopics(body: Record<string, unknown>) {
  const category = typeof body.category === "string" ? body.category : "生活方式";
  const keywords = Array.isArray(body.keywords) ? body.keywords.filter((item): item is string => typeof item === "string") : [];
  const count = Math.min(Math.max(Number(body.count) || 15, 1), 50);
  const subject = keywords[0] || category;
  const hooks = ["你还在这样做吗？", "3秒看懂一个关键变化", "我试了7天，结果出乎意料", "别急着买，先看这一个细节", "为什么大家最近都在讨论它？"];
  return Array.from({ length: count }, (_, index) => ({
    title: `${subject}创作灵感 ${index + 1}：把一个小变化拍出大反差`,
    hook_suggestion: hooks[index % hooks.length],
    content_direction: `围绕${subject}设计真实场景，用前后对比和可验证的细节提升完播率。`,
    target_platform: [typeof body.target_platform === "string" ? body.target_platform : "抖音"],
    target_duration: index % 2 ? "30-45秒" : "45-60秒",
    estimated_viral_potential: 72 + (index % 9),
    supporting_trends: ["真实体验", "沉浸式叙事"],
    reference_patterns: ["问题开场", "对比转折"],
    key_selling_points: ["低成本可执行", "开头3秒有冲突"],
    risk_factors: ["避免夸大宣传"],
    script_outline: "开场提出问题 → 展示真实过程 → 给出结论和行动建议",
    visual_concept: "明亮自然光，近景细节与手持跟拍结合",
    tags: [category, subject],
  }));
}

function demoTrends(platform?: string, category?: string) {
  const updated = demoNow();
  const platformNames: Record<string, string> = {
    douyin: "抖音",
    xiaohongshu: "小红书",
    bilibili: "B站",
    weibo: "微博",
    kuaishou: "快手",
  };
  const allTrends = [
    { id: "demo-trend-1", platform: "抖音", title: "沉浸式真实体验", category: "生活", hot_value: 920000, hot_value_growth: 1.28, rank_position: 1, tags: ["沉浸式", "真实体验"], status: "active", lifecycle_stage: "rising", last_updated_at: updated },
    { id: "demo-trend-2", platform: "小红书", title: "一周使用前后对比", category: "3C", hot_value: 680000, hot_value_growth: 0.86, rank_position: 3, tags: ["测评", "对比"], status: "active", lifecycle_stage: "rising", last_updated_at: updated },
    { id: "demo-trend-3", platform: "B站", title: "低成本电影感教程", category: "知识", hot_value: 410000, hot_value_growth: 0.43, rank_position: 8, tags: ["教程", "电影感"], status: "active", lifecycle_stage: "stable", last_updated_at: updated },
  ];
  const selectedPlatform = platformNames[platform || ""];
  const trends = allTrends.filter((trend) =>
    (!selectedPlatform || trend.platform === selectedPlatform) && (!category || trend.category === category)
  );
  const risingAlerts = trends.filter((trend) => trend.lifecycle_stage === "rising").map((trend) => ({
    title: trend.title,
    platform: trend.platform,
    category: trend.category,
    growth_rate: trend.hot_value_growth,
    hot_value: trend.hot_value,
    urgency: trend.hot_value_growth >= 1 ? "high" : "medium",
    recommended_action: trend.hot_value_growth >= 1 ? "48小时内完成首条测试内容" : "本周完成一条验证内容",
  }));
  return {
    summary: "演示热点数据：建议优先关注真实体验、沉浸式叙事和前后对比。",
    total_topics: trends.length,
    rising_alerts: risingAlerts,
    cross_platform_trends: [{ title: "前后对比", platforms: ["抖音", "小红书"], momentum: "rising" }],
    trends,
  };
}
function demoViralVideos() {
  const demoShots = Array.from({ length: 8 }, (_, index) => {
    const durations = [2.8, 4.2, 5.1, 4.6, 4.8, 5.0, 5.2, 6.3];
    const start = durations.slice(0, index).reduce((total, value) => total + value, 0);
    return {
      id: `demo-shot-${index + 1}`,
      shot_index: index,
      start_time: Number(start.toFixed(1)),
      end_time: Number((start + durations[index]).toFixed(1)),
      duration: durations[index],
      transcript: ["先别急着买", "我先看了包装细节", "真正影响体验的是这里", "开机后对比一下", "这个变化很明显", "日常使用更顺手", "如果你也在考虑", "收藏起来再决定"][index],
      visual_description: ["产品包装与隐藏细节的快速特写", "手指翻开包装，展示关键部件", "镜头推近接口和材质纹理", "左右分屏对比使用前后", "手持设备完成连续操作", "桌面场景展示真实使用状态", "人物面对镜头给出购买建议", "产品与结论字幕定格"][index],
      emotion_tag: ["悬念", "好奇", "惊喜", "对比", "认可", "安心", "信任", "行动"][index],
      transition_type: index === 0 ? "cut" : index === 3 ? "match" : "cut",
      motion_intensity: [0.8, 0.5, 0.6, 0.7, 0.4, 0.3, 0.2, 0.1][index],
      onset_strength: [0.9, 0.6, 0.7, 0.8, 0.5, 0.4, 0.3, 0.2][index],
    };
  });
  const analysis = {
    narrative_structure: { name: "问题—验证—结论", phases: ["痛点开场", "细节验证", "前后对比", "购买建议"] },
    visual_language: { shot_style: "近景特写为主", composition: "中心构图与左右对比", color: "明亮自然、高对比" },
    rhythm_analysis: { average_shot_duration: 4.75, bpm: 124, pacing: "前3秒快速，结尾留出结论停顿" },
  };
  return [
    { id: "demo-viral-1", platform: "抖音", video_id: "demo-viral-1", url: "https://example.com/demo-viral-1", author_name: "Mago 示例账号", title: "一个细节让开箱视频完播率翻倍", description: "演示数据，仅用于体验工作台交互", tags: ["开箱", "数码", "对比"], category: "3C", duration: 38, width: 1080, height: 1920, aspect_ratio: "9:16", metrics: { likes: 128000, comments: 3200, shares: 5600 }, viral_score: 91, analysis_status: "completed", shot_count: 8, avg_shot_duration: 4.75, hook_text: "先别买，看看这个隐藏细节", hook_type: "pain_point", hook_engagement_score: 0.88, bgm_bpm: 124, bgm_emotion: "紧张后转轻快", transcript: "先别急着买，我先把这个容易忽略的细节给你看。", narrative_structure: analysis.narrative_structure, visual_language: analysis.visual_language, rhythm_analysis: analysis.rhythm_analysis, analysis, shots: demoShots, analyzed_at: demoNow(1) },
    { id: "demo-viral-2", platform: "小红书", video_id: "demo-viral-2", url: "https://example.com/demo-viral-2", author_name: "Mago 示例账号", title: "7天真实使用后的变化", description: "演示数据，仅用于体验工作台交互", tags: ["真实体验", "生活"], category: "生活", duration: 52, width: 1080, height: 1440, aspect_ratio: "3:4", metrics: { likes: 86000, comments: 1800, shares: 2900 }, viral_score: 86, analysis_status: "completed", shot_count: 10, avg_shot_duration: 5.2, hook_text: "我本来以为不会有变化", hook_type: "story", hook_engagement_score: 0.81, bgm_bpm: 98, bgm_emotion: "温暖", analyzed_at: demoNow(2) },
  ];
}
function demoPromptPackage(projectId: string) {
  const pkg = { id: `demo-package-${projectId}`, project_id: projectId, storyboard_id: "demo-storyboard", version: 1, name: "演示提示词包", status: "ready", total_shots: 3, selected_models: ["SDXL", "Runway"], global_parameters: { aspect_ratio: "9:16" } };
  const prompts = [1, 2, 3].map((shot) => ({ id: `demo-prompt-${shot}`, package_id: pkg.id, shot_id: String(shot), model_id: shot === 3 ? "Runway" : "SDXL", prompt_type: "positive", positive_prompt: `cinematic vertical video, shot ${shot}, natural light, detailed composition, consistent character`, negative_prompt: "blurry, low quality, deformed hands", parameters: { aspect_ratio: "9:16" } }));
  return { pkg, prompts };
}

function demoKnowledge(url: string) {
  const query = new URL(url, "http://mago.local").searchParams.get("q") || "创意";
  return { results: [{ name: `关于“${query}”的创作建议`, category: "创意理论", score: 0.94, content: "用具体冲突替代空泛描述，在前3秒给出明确问题，并用可验证的过程支撑结论。", example: "先展示结果，再倒叙解释过程。", tags: ["钩子", "完播率"] }] };
}

/** Return deterministic, stateful local data for an explicitly enabled demo session. */
function getMockData<T>(url: string, options: RequestInit): T {
  const method = (options.method || "GET").toUpperCase();
  const body = readJsonBody(options);

  if (url.includes("/projects")) {
    const projects = demoProjects();
    const projectId = url.match(/\/projects\/([^?/#]+)/)?.[1];
    if (method === "POST" && !projectId) {
      const project = { id: `demo-project-${Date.now()}`, name: String(body.name || "未命名项目"), description: String(body.description || ""), status: "draft", aspect_ratio: String(body.aspect_ratio || "9:16"), created_at: demoNow(), updated_at: demoNow() };
      writeDemoList(DEMO_PROJECTS_KEY, [project, ...projects]);
      return project as T;
    }
    if (projectId && method === "DELETE") {
      const project = projects.find((item) => item.id === projectId);
      if (!project) throw new Error("项目不存在");
      writeDemoList(DEMO_PROJECTS_KEY, projects.filter((item) => item.id !== projectId));
      return undefined as T;
    }
    if (projectId && method === "PUT") {
      const project = projects.find((item) => item.id === projectId);
      if (!project) throw new Error("项目不存在");
      const updated = projects.map((item) => item.id === projectId ? { ...item, ...body, updated_at: demoNow() } : item);
      writeDemoList(DEMO_PROJECTS_KEY, updated);
      return updated.find((item) => item.id === projectId) as T;
    }
    if (projectId) {
      const project = projects.find((item) => item.id === projectId);
      if (!project) throw new Error("项目不存在");
      return project as T;
    }
    return { items: projects, total: projects.length, page: 1, page_size: 50 } as T;
  }

  if (url.includes("/characters")) {
    const characters = demoCharacters();
    const characterId = url.match(/\/characters\/([^?/#]+)/)?.[1];
    if (method === "POST" && !characterId) {
      const character = { id: `demo-character-${Date.now()}`, owner_id: "demo", ...body, tags: [], is_preset: false, created_at: demoNow(), updated_at: demoNow() };
      writeDemoList(DEMO_CHARACTERS_KEY, [character, ...characters]);
      return character as T;
    }
    if (characterId && method === "DELETE") {
      const character = characters.find((item) => item.id === characterId);
      if (!character) throw new Error("角色不存在");
      writeDemoList(DEMO_CHARACTERS_KEY, characters.filter((item) => item.id !== characterId));
      return undefined as T;
    }
    if (characterId) {
      const character = characters.find((item) => item.id === characterId);
      if (!character) throw new Error("角色不存在");
      return character as T;
    }
    return { items: characters, total: characters.length, page: 1, page_size: 20 } as T;
  }

  if (url.includes("/topic-recommendations/generate")) return { topics: demoTopics(body), trend_summary: "演示模式：已根据你的领域和关键词生成可执行选题。", model_info: { mode: "demo" }, generated_at: demoNow() } as T;
  if (url.includes("/trends/crawl-now")) return { task_id: `demo-task-${Date.now()}`, status: "queued" } as T;
  if (url.includes("/trends/insights")) {
    const query = new URL(url, "http://mago.local").searchParams;
    return demoTrends(query.get("platform") || undefined, query.get("category") || undefined) as T;
  }
  if (url.includes("/viral-videos/analyze")) return { task_id: `demo-analysis-${Date.now()}`, status: "queued", url: String(body.url || "") } as T;
  if (url.includes("/viral-videos")) {
    const videos = demoViralVideos();
    const videoId = url.match(/\/viral-videos\/([^?/#]+)/)?.[1];
    if (videoId) {
      const video = videos.find((item) => item.id === videoId);
      if (!video) throw new Error("爆款视频不存在");
      return video as T;
    }
    return { items: videos, total: videos.length, page: 1, page_size: 20 } as T;
  }
  if (url.includes("/knowledge/search")) return demoKnowledge(url) as T;
  if (url.includes("/prompt-packages/")) {
    const packageId = url.match(/\/prompt-packages\/([^?/#]+)/)?.[1] || "";
    const projectId = packageId.startsWith("demo-package-") ? packageId.slice("demo-package-".length) : "demo";
    return demoPromptPackage(projectId) as T;
  }
  if (url.includes("/prompt-packages")) {
    const projectId = new URL(url, "http://mago.local").searchParams.get("project_id") || "demo";
    return [demoPromptPackage(projectId).pkg] as T;
  }
  if (url.includes("/me")) return { id: "demo", email: "test@example.com", name: "演示用户", role: "user" } as T;
  return {} as T;
}

function demoEvent(event: string, data: unknown): string {
  return `event: ${event}\ndata: ${JSON.stringify(data)}\n\n`;
}

function demoAgentPayload(options: RequestInit): Record<string, unknown> {
  if (typeof options.body !== "string") return {};
  try {
    const value: unknown = JSON.parse(options.body);
    return typeof value === "object" && value !== null ? value as Record<string, unknown> : {};
  } catch {
    return {};
  }
}

/** Marker used by demo-mode streams; the UI shows it verbatim as provenance. */
export const DEMO_MODEL = "demo-mock";

/** A browser-native SSE response used by ChatInterface and useChatStream in demo mode. */
function createDemoAgentResponse(options: RequestInit): Response {
  const payload = demoAgentPayload(options);
  const message = String(payload.message || "你的创作想法");
  const mode = String(payload.mode || "detailed");
  const selectedIdeaId = typeof payload.selected_idea_id === "string" ? payload.selected_idea_id : undefined;
  const ideas = [1, 2, 3].map((index) => ({ id: `demo-idea-${index}`, title: `${message.slice(0, 18)} · 创意方向 ${index}`, description: `将“${message}”转化为一个有明确冲突、真实细节和可执行镜头的短视频方案。`, hook_direction: ["先给结果，再解释原因", "用一个反常识问题开场", "展示前后对比制造停留"][index - 1], emotion_tone: ["惊喜", "好奇", "共鸣"][index - 1], differentiation: "低成本、强细节、适合连续更新", ai_feasibility_score: 8 + (index % 2), difficulty: index === 3 ? "medium" : "low", estimated_duration: 35 + index * 5, tags: ["演示", "可执行"], is_hot_trend: index === 1 }));
  const chosen = ideas.find((idea) => idea.id === selectedIdeaId) || ideas[0];
  const script = { title: chosen.title, hook_type: "contrast", structure_id: "problem-solution", target_duration_sec: 45, hook: chosen.hook_direction, hook_variants: [{ hook_type: "question", text: "你是不是也遇到过同样的问题？" }], body_text: `围绕${message}展开真实体验，展示关键步骤、对比结果和最终建议。`, beats: [{ phase: "hook", duration_sec: 3, content: chosen.hook_direction, visual_note: "结果特写，快速推近" }, { phase: "body", duration_sec: 32, content: "展示过程与关键细节", visual_note: "中近景跟拍，穿插细节特写" }, { phase: "cta", duration_sec: 10, content: "给出清晰建议并邀请互动", visual_note: "正面出镜，字幕强调行动" }], cta: "收藏这条视频，下次拍摄直接照着做。" };
  const storyboard = { title: `${chosen.title} · 分镜表`, shot_count: 3, total_duration_sec: 45, aspect_ratio: "9:16", visual_style_notes: "自然光、清爽高对比、轻微手持感，保持角色和场景连续。", shots: [
    { index: 1, duration_sec: 3, shot_size: "特写", camera_angle: "平视", camera_movement: "推近", lighting: "自然光", color_tone: "清爽", visual_description: "关键结果的细节特写", dialogue: chosen.hook_direction, transition: "cut", ai_generation_difficulty: 3, ai_warnings: [] },
    { index: 2, duration_sec: 32, shot_size: "中景", camera_angle: "平视", camera_movement: "跟拍", lighting: "柔光", color_tone: "自然", visual_description: "展示真实过程和关键步骤", dialogue: "看这里，最重要的是这个细节。", transition: "match", ai_generation_difficulty: 5, ai_warnings: [] },
    { index: 3, duration_sec: 10, shot_size: "近景", camera_angle: "平视", camera_movement: "固定", lighting: "柔光", color_tone: "明亮", visual_description: "出镜总结并给出行动建议", dialogue: "收藏起来，下次直接用。", transition: "fade", ai_generation_difficulty: 4, ai_warnings: [] },
  ] };
  const includeScript = mode === "quick" || Boolean(selectedIdeaId);
  const includeStoryboard = includeScript && mode !== "ideation";
  // Demo mode has no backend at all: say so on the wire, so the UI can label
  // the result honestly instead of implying a model produced it.
  const demoProvenance = { llm_configured: false, model: DEMO_MODEL };
  const events = [demoEvent("meta", { run_id: "demo", mode, timestamp: Date.now() / 1000, ...demoProvenance }), demoEvent("thinking", { text: "正在整理创作方向…" }), demoEvent("chunk", { text: `已收到你的想法：“${message}”。我先给你一个可直接执行的创作方案。` }), demoEvent("ideas", { ideas }), ...(includeScript ? [demoEvent("script", { script, ...demoProvenance })] : []), ...(includeStoryboard ? [demoEvent("storyboard", { storyboard, ...demoProvenance })] : []), demoEvent("done", { state: { mode: "demo" } })];
  const encoder = new TextEncoder();
  const signal = options.signal;
  const stream = new ReadableStream<Uint8Array>({
    async start(controller) {
      let closed = false;
      const close = () => {
        if (closed) return;
        closed = true;
        try {
          controller.close();
        } catch {
          // The consumer may have cancelled the stream already.
        }
      };
      const abort = () => close();
      signal?.addEventListener("abort", abort, { once: true });
      try {
        for (const event of events) {
          if (signal?.aborted || closed || controller.desiredSize === null) break;
          try {
            controller.enqueue(encoder.encode(event));
          } catch {
            // The consumer may cancel the response while the demo producer is
            // waiting. A cancelled ReadableStream must not enqueue or close.
            break;
          }
          await new Promise((resolve) => setTimeout(resolve, 30));
        }
      } finally {
        signal?.removeEventListener("abort", abort);
        close();
      }
    },
  });
  return new Response(stream, { status: 200, headers: { "Content-Type": "text/event-stream; charset=utf-8", "Cache-Control": "no-cache" } });
}
