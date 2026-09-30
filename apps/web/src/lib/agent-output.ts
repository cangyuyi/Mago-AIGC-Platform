/**
 * Typed description of the payloads the Python agent emits over SSE.
 *
 * These shapes used to be `any` all the way through the UI, which meant a
 * rename on the agent side silently produced empty cards instead of an error.
 * Every field here is optional except the ones the renderer really needs, so
 * older agent versions still render instead of crashing.
 */

export interface AgentHookVariant {
  hook_type?: string;
  text?: string;
  reason?: string;
}

export interface AgentBeat {
  phase?: string;
  duration_sec?: number;
  content?: string;
  visual_note?: string;
  emotion?: string;
}

export interface AgentScript {
  id?: string;
  title?: string;
  script_type?: string;
  target_duration_sec?: number;
  aspect_ratio?: string;
  target_platform?: string;
  hook?: string;
  hook_type?: string;
  hook_variants?: AgentHookVariant[];
  body_text?: string;
  beats?: AgentBeat[];
  cta?: string;
  cta_type?: string;
  tags?: string[];
  emotion_arc?: string[];
  quality_scores?: Record<string, number>;
  compliance_flags?: Array<{ level?: string; reason?: string; suggestion?: string }>;
  /** Present when the agent answered from a template because no LLM key is set. */
  model_info?: Record<string, unknown>;
  generated_by?: string;
}

export interface AgentShot {
  index?: number;
  duration_sec?: number;
  shot_size?: string;
  camera_angle?: string;
  camera_movement?: string;
  /** The agent writes `scene_description`; the stored column is `scene_environment`. */
  scene_description?: string;
  scene_environment?: string;
  subject_description?: string;
  props?: string[];
  emotion?: string;
  visual_description?: string;
  action_description?: string;
  dialogue?: string;
  sound_effect?: string;
  lighting?: string;
  color_tone?: string;
  transition?: string;
  ai_warnings?: string[];
}

export interface AgentStoryboard {
  id?: string;
  title?: string;
  total_duration_sec?: number;
  shot_count?: number;
  aspect_ratio?: string;
  visual_style_notes?: string;
  shots?: AgentShot[];
  model_info?: Record<string, unknown>;
}

/** True when the payload carries real content we can show or store. */
export function hasScriptContent(script: AgentScript | null | undefined): boolean {
  if (!script) return false;
  return Boolean(script.title || script.hook || script.body_text || script.cta || script.beats?.length);
}

export function hasStoryboardContent(storyboard: AgentStoryboard | null | undefined): boolean {
  return Boolean(storyboard?.shots?.length || storyboard?.title);
}

/** Number of shots, preferring the explicit count but never trusting a lie. */
export function shotCount(storyboard: AgentStoryboard | null | undefined): number {
  const actual = storyboard?.shots?.length ?? 0;
  if (!actual) return Number(storyboard?.shot_count ?? 0);
  return actual;
}

/**
 * Detects offline/template answers so the UI can label them. The agent reports
 * the model it used in `model_info`; when it says "template"/"offline" or
 * reports no model at all, the output is not a real LLM generation.
 */
export function isTemplateOutput(payload: { model_info?: Record<string, unknown>; generated_by?: string } | null | undefined): boolean {
  if (!payload) return false;
  const info = payload.model_info ?? {};
  const candidates = [
    info.mode, info.provider, info.model, info.engine, payload.generated_by,
  ];
  if (candidates.some((value) => typeof value === "string" && /template|offline|mock|demo|fallback/i.test(value))) return true;
  // No model identity at all: we cannot claim a real model produced this.
  return candidates.every((value) => typeof value !== "string" || value.trim() === "");
}
