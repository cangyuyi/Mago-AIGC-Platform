// ===== Mago Agent Platform - Shared TypeScript Types =====

// ------ Common ------
export interface PaginationParams {
  page: number;
  page_size: number;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
}

export interface ApiResponse<T = unknown> {
  code: number;
  message: string;
  data?: T;
}

// ------ Auth ------
export interface User {
  id: string;
  email: string;
  name: string;
  avatar_url?: string;
  org_id?: string;
  role: "owner" | "admin" | "editor" | "viewer";
  created_at: string;
  updated_at: string;
}

export interface LoginRequest {
  email: string;
  password: string;
}

export interface LoginResponse {
  access_token: string;
  refresh_token: string;
  user: User;
}

export interface RegisterRequest {
  email: string;
  password: string;
  name: string;
}

// ------ Projects ------
// The Go API currently accepts and returns open-ended strings for these fields.
export type ProjectStatus = string;

export interface Project {
  id: string;
  name: string;
  description?: string;
  status: ProjectStatus;
  aspect_ratio: string;
  target_platform?: string;
  target_duration?: number;
  category?: string;
  cover_image_url?: string;
  owner_id: string;
  org_id?: string;
  current_step?: ProjectStep;
  character_ids: string[];
  style_preset_ids: string[];
  reference_video_ids: string[];
  created_at: string;
  updated_at: string;
}

// ProjectService.Update accepts any current_step string; keep this API contract open.
export type ProjectStep = string;

export interface CreateProjectRequest {
  name: string;
  description?: string;
  aspect_ratio?: string;
  target_platform?: string;
  target_duration?: number;
  category?: string;
}

export interface UpdateProjectRequest {
  name?: string;
  description?: string;
  status?: ProjectStatus;
  current_step?: ProjectStep;
}

// ------ Scripts ------
export type ScriptType =
  | "oral_sharing"
  | "story_drama"
  | "product_showcase"
  | "review_seeding"
  | "tutorial"
  | "brand_tvc"
  | "hot_topic"
  | "vlog"
  | "other";

export type ScriptStatus = "draft" | "reviewing" | "approved" | "final";

export interface Script {
  id: string;
  project_id: string;
  version: number;
  title: string;
  script_type: ScriptType;
  duration_target?: number;
  aspect_ratio: string;
  target_platform?: string;
  status: ScriptStatus;
  hook?: string;
  hook_type?: string;
  body?: string;
  cta?: string;
  cta_type?: string;
  tags: string[];
  emotion_arc: string[];
  quality_scores: Record<string, number>;
  quality_feedback: Array<{ dimension: string; score: number; suggestion: string }>;
  compliance_flags: Array<{ level: "pass" | "warning" | "danger"; reason: string; suggestion: string }>;
  created_at: string;
  updated_at: string;
}

export interface CreativeIdea {
  id: string;
  title: string;
  description: string;
  hook_direction?: string;
  emotion_tone: string;
  differentiation: string;
  ai_feasibility_score: number;
  difficulty: "low" | "medium" | "high";
  estimated_duration: number;
  reference_video_ids: string[];
  tags: string[];
  is_hot_trend: boolean;
}

// ------ Storyboard ------
export type ShotType =
  | "extreme_close_up"
  | "close_up"
  | "medium_close_up"
  | "medium"
  | "medium_wide"
  | "wide"
  | "extreme_wide"
  | "pov"
  | "over_shoulder";

export type CameraMovement =
  | "static"
  | "push_in"
  | "push_out"
  | "pan_left"
  | "pan_right"
  | "tilt_up"
  | "tilt_down"
  | "tracking"
  | "following"
  | "crane_up"
  | "crane_down"
  | "orbit"
  | "handheld"
  | "zoom_in"
  | "zoom_out"
  | "whip_pan";

export interface StoryboardShot {
  id: string;
  storyboard_id: string;
  shot_index: number;
  duration: number;
  shot_type: ShotType;
  camera_movement?: CameraMovement;
  camera_angle?: string;
  scene_environment: string;
  subject_description: string;
  props: string[];
  lighting?: string;
  color_tone?: string;
  composition?: string;
  dialogue_narration?: string;
  sound_effect?: string;
  bgm_emotion?: string;
  emotion_tag?: string;
  transition_in?: string;
  transition_out?: string;
  motion_description?: string;
  ai_generation_notes?: string;
  consistency_hints: Record<string, boolean>;
  quality_score?: number;
  feedback?: string;
  created_at: string;
  updated_at: string;
}

export interface Storyboard {
  id: string;
  project_id: string;
  script_id: string;
  version: number;
  title: string;
  total_duration: number;
  shot_count: number;
  aspect_ratio: string;
  status: "draft" | "reviewing" | "approved";
  shots: StoryboardShot[];
  created_at: string;
  updated_at: string;
}

// ------ Chat / Agent Streaming ------
export interface ChatMessage {
  id: string;
  role: "user" | "agent" | "system";
  content: string;
  content_blocks?: ContentBlock[];
  created_at: string;
}

export type ContentBlock =
  | { type: "text"; text: string }
  | { type: "ideas"; ideas: CreativeIdea[] }
  | { type: "script"; script: Script }
  | { type: "shots"; shots: StoryboardShot[] }
  | { type: "error"; message: string };

export type AgentEventType =
  | "node_start"
  | "node_progress"
  | "node_complete"
  | "hitl_required"
  | "message_chunk"
  | "message_complete"
  | "error"
  | "completed";

export interface AgentEvent {
  type: AgentEventType;
  node_name?: string;
  project_id: string;
  run_id: string;
  data?: unknown;
  timestamp: string;
}

// ------ Characters & Styles ------
// Mirrors the Go Character JSON model. Reference images are a separate resource,
// not an embedded field on the character response.
export interface Character {
  id: string;
  owner_id: string;
  org_id?: string;
  visibility: string;
  name: string;
  description?: string;
  gender?: string;
  age_appearance?: string;
  ethnicity?: string;
  face_description?: string;
  hair_description?: string;
  body_description?: string;
  clothing_default?: string;
  skin_details?: string;
  distinctive_features: string[];
  personality_vibe?: string;
  faceid_weight: number;
  ip_adapter_scale: number;
  reference_strategy: string;
  seed_base?: number;
  model_compatibility: Record<string, unknown>;
  prompt_fragment: string;
  negative_fragment?: string;
  tags: string[];
  is_preset: boolean;
  created_at: string;
  updated_at: string;
}

export interface CreateCharacterRequest {
  name: string;
  prompt_fragment: string;
  description?: string;
  gender?: string;
  age_appearance?: string;
  personality_vibe?: string;
  tags?: string[];
}

export interface StylePreset {
  id: string;
  name: string;
  category: string;
  description?: string;
  positive_fragment: string;
  negative_fragment?: string;
  dominant_colors?: string[];
  lighting_style?: string;
  color_tone?: string;
  lens_and_camera?: string;
  parameter_hints: Record<string, unknown>;
  recommended_loras: Array<{ name: string; weight: number; trigger_words: string[] }>;
  tags: string[];
  example_image_url?: string;
  is_preset: boolean;
  created_at: string;
}

// ------ Prompts ------
export interface PromptPackage {
  id: string;
  project_id: string;
  storyboard_id: string;
  version: number;
  name: string;
  status: string;
  total_shots: number;
  selected_models: string[] | null;
  global_parameters: Record<string, unknown> | null;
  created_at: string;
  updated_at: string;
}

export interface Prompt {
  id: string;
  package_id: string;
  shot_id: string;
  model_id: string;
  prompt_type: string;
  positive_prompt: string;
  negative_prompt?: string;
  parameters: Record<string, unknown> | null;
  reference_images: unknown;
  lora_triggers: unknown;
  seed_value?: number;
  seed_locked: boolean;
  consistency_notes?: string;
  version: number;
  quality_score: Record<string, unknown> | null;
  exported_to_mago: boolean;
  user_modified: boolean;
  created_by: string;
  created_at: string;
  updated_at: string;
}

// ------ Trends & Viral Videos ------
export interface TrendTopic {
  id: string;
  platform: string;
  title: string;
  category?: string;
  hot_value?: number;
  hot_value_growth?: number;
  rank_position?: number;
  status: string;
  tags: string[];
  url?: string;
  cover_url?: string;
  last_updated_at: string;
}

export interface ViralVideo {
  id: string;
  platform: string;
  url: string;
  title?: string;
  author_name?: string;
  category?: string;
  duration?: number;
  aspect_ratio?: string;
  metrics: Record<string, number>;
  viral_score?: number;
  analysis_status: string;
  analysis?: Record<string, unknown>;
  thumbnail_url?: string;
  created_at: string;
}
