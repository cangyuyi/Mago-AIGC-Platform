/**
 * Generation persistence.
 *
 * Two backends on purpose:
 *   - API    : the real PostgreSQL-backed store, used whenever the session is
 *              authenticated against a gateway and the project id is a UUID.
 *   - Local  : browser storage for demo sessions and for projects that only
 *              exist in the UI. Without it a refresh destroyed every script.
 * The active backend is always reported to the caller so the UI can never
 * claim a save the user cannot verify.
 */
import { apiFetch, isDemoMode } from "./auth";
import type { AgentScript, AgentStoryboard } from "./agent-output";

export type StorageKind = "api" | "local";

export interface SavedGeneration {
  id: string;
  project_id: string;
  created_at: string;
  storage: StorageKind;
  llm_configured: boolean;
  script: AgentScript;
  storyboard: AgentStoryboard | null;
}

export interface GenerationProvenance {
  llm_configured?: boolean;
  model?: string;
}

const LOCAL_KEY_PREFIX = "mago.generations.";
const MAX_LOCAL_GENERATIONS = 50;

const UUID_PATTERN = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

export function isUuid(value: string | null | undefined): value is string {
  return typeof value === "string" && UUID_PATTERN.test(value);
}

/** Which backend will a save for this session/project land in? */
export function resolveStorage(projectId: string | null | undefined): StorageKind {
  if (!projectId) return "local";
  if (isDemoMode()) return "local";
  return isUuid(projectId) ? "api" : "local";
}

function localKey(projectId: string): string {
  return `${LOCAL_KEY_PREFIX}${projectId || "default"}`;
}

function readLocal(projectId: string): SavedGeneration[] {
  if (typeof window === "undefined") return [];
  try {
    const raw = window.localStorage.getItem(localKey(projectId));
    const parsed: unknown = raw ? JSON.parse(raw) : [];
    if (!Array.isArray(parsed)) return [];
    return parsed.filter(isSavedGeneration);
  } catch {
    return [];
  }
}

function isSavedGeneration(value: unknown): value is SavedGeneration {
  if (typeof value !== "object" || value === null) return false;
  const candidate = value as Partial<SavedGeneration>;
  return typeof candidate.id === "string" && !!candidate.script && typeof candidate.script === "object";
}

function writeLocal(entries: SavedGeneration[]): void {
  if (typeof window === "undefined") return;
  const trimmed = entries.slice(0, MAX_LOCAL_GENERATIONS);
  try {
    window.localStorage.setItem(localKey(trimmed[0]?.project_id || ""), JSON.stringify(trimmed));
  } catch {
    throw new Error("浏览器本地存储空间不足，请删除旧的生成结果或连接后端服务");
  }
}

// ---------------------------------------------------------------- API payloads

interface ScriptRow {
  id: string;
  project_id: string;
  version: number;
  title: string;
  script_type: string;
  duration_target?: number;
  aspect_ratio?: string;
  target_platform?: string;
  status: string;
  hook?: string;
  hook_type?: string;
  body?: string;
  cta?: string;
  tags?: string[];
  emotion_arc?: string[];
  creative_brief?: Record<string, unknown>;
  model_info?: Record<string, unknown>;
  created_at?: string;
  updated_at?: string;
}

interface StoryboardRow {
  id: string;
  project_id: string;
  script_id: string;
  version: number;
  title: string;
  total_duration: number;
  shot_count: number;
  aspect_ratio?: string;
  status: string;
  model_info?: Record<string, unknown>;
  created_at?: string;
}

/** Keep the agent payload verbatim so re-rendering never loses a field. */
function toScriptRow(projectId: string, script: AgentScript, provenance: GenerationProvenance): ScriptRow {
  return {
    id: crypto.randomUUID(),
    project_id: projectId,
    version: 1,
    title: script.title || "未命名脚本",
    script_type: script.script_type || "oral_sharing",
    duration_target: script.target_duration_sec,
    aspect_ratio: script.aspect_ratio || "9:16",
    target_platform: script.target_platform,
    status: "draft",
    hook: script.hook,
    hook_type: script.hook_type,
    body: script.body_text,
    cta: script.cta,
    tags: script.tags || [],
    emotion_arc: script.emotion_arc || [],
    creative_brief: { agent_script: script },
    model_info: { llm_configured: provenance.llm_configured ?? null, model: provenance.model || null },
  };
}

function toStoryboardRow(projectId: string, scriptId: string, storyboard: AgentStoryboard, provenance: GenerationProvenance): StoryboardRow {
  return {
    id: crypto.randomUUID(),
    project_id: projectId,
    script_id: scriptId,
    version: 1,
    title: storyboard.title || "未命名分镜",
    total_duration: storyboard.total_duration_sec || 0,
    shot_count: storyboard.shots?.length || 0,
    aspect_ratio: storyboard.aspect_ratio || "9:16",
    status: "draft",
    model_info: {
      llm_configured: provenance.llm_configured ?? null,
      model: provenance.model || null,
      agent_storyboard: storyboard,
    },
  };
}

/** Agent shot names are not column names; map them to the persisted schema. */
export function toShotRows(storyboard: AgentStoryboard) {
  return (storyboard.shots || []).map((shot, index) => ({
    shot_index: shot.index ?? index + 1,
    duration: shot.duration_sec ?? 0,
    shot_type: shot.shot_size || "",
    camera_angle: shot.camera_angle || "",
    camera_movement: shot.camera_movement || "",
    scene_environment: shot.scene_description || shot.scene_environment || "未指定",
    subject_description: shot.subject_description || shot.visual_description || shot.action_description || "未指定",
    lighting: shot.lighting || "",
    color_tone: shot.color_tone || "",
    dialogue_narration: shot.dialogue || "",
    sound_effect: shot.sound_effect || "",
    transition_out: shot.transition || "",
    motion_description: shot.action_description || "",
    ai_generation_notes: (shot.ai_warnings || []).join("；"),
  }));
}

function rowToScript(row: ScriptRow): AgentScript {
  const stored = row.creative_brief?.agent_script as AgentScript | undefined;
  if (stored && typeof stored === "object") return stored;
  return {
    title: row.title,
    hook: row.hook,
    hook_type: row.hook_type,
    body_text: row.body,
    cta: row.cta,
    aspect_ratio: row.aspect_ratio,
    target_platform: row.target_platform,
    target_duration_sec: row.duration_target,
    tags: row.tags,
    emotion_arc: row.emotion_arc,
  };
}

function storyboardRowToAgent(row: StoryboardRow, shots: AgentStoryboard["shots"]): AgentStoryboard {
  const stored = row.model_info?.agent_storyboard as AgentStoryboard | undefined;
  if (stored && typeof stored === "object") return stored;
  return {
    title: row.title,
    total_duration_sec: row.total_duration,
    shot_count: row.shot_count,
    aspect_ratio: row.aspect_ratio,
    shots: shots || [],
  };
}

// ------------------------------------------------------------------- Save/list

/** Persist one generation. Throws with a human-readable Chinese message. */
export async function saveGeneration(
  projectId: string | null | undefined,
  payload: { script?: AgentScript | null; storyboard?: AgentStoryboard | null },
  provenance: GenerationProvenance = {}
): Promise<SavedGeneration> {
  if (!payload.script && !payload.storyboard) throw new Error("没有可保存的内容");
  const owner = projectId || "default";
  const generation: SavedGeneration = {
    id: crypto.randomUUID(),
    project_id: owner,
    created_at: new Date().toISOString(),
    storage: resolveStorage(projectId),
    llm_configured: provenance.llm_configured ?? false,
    script: payload.script || ({} as AgentScript),
    storyboard: payload.storyboard || null,
  };

  if (generation.storage === "local") {
    const entries = readLocal(owner);
    entries.unshift(generation);
    writeLocal(entries);
    return generation;
  }

  const scriptRow = toScriptRow(owner, generation.script, provenance);
  // The gateway keeps client-supplied ids, but never assume it: trust whatever
  // came back, otherwise the storyboard/shots and the delete button would point
  // at a row that does not exist.
  const createdScript = await apiFetch<Partial<ScriptRow>>("/api/v1/scripts", { method: "POST", body: JSON.stringify(scriptRow) });
  generation.id = createdScript?.id || scriptRow.id;

  if (generation.storyboard) {
    const sbRow = toStoryboardRow(owner, generation.id, generation.storyboard, provenance);
    const createdBoard = await apiFetch<Partial<StoryboardRow>>("/api/v1/storyboards", { method: "POST", body: JSON.stringify(sbRow) });
    const storyboardId = createdBoard?.id || sbRow.id;
    const shots = toShotRows(generation.storyboard);
    if (shots.length) {
      await apiFetch(`/api/v1/storyboards/${storyboardId}/shots`, { method: "PUT", body: JSON.stringify({ shots }) });
    }
  }
  return generation;
}

/** All generations for a project, newest first, from whichever backend owns them. */
export async function listGenerations(projectId: string | null | undefined): Promise<SavedGeneration[]> {
  if (resolveStorage(projectId) === "local") return readLocal(projectId || "default");

  try {
    const scripts = await apiFetch<ScriptRow[]>(`/api/v1/scripts?project_id=${encodeURIComponent(projectId as string)}`);
    const storyboards = await apiFetch<StoryboardRow[]>(`/api/v1/storyboards?project_id=${encodeURIComponent(projectId as string)}`);
    const rows = Array.isArray(scripts) ? scripts : [];
    const sbRows = Array.isArray(storyboards) ? storyboards : [];

    return rows
      .map((row): SavedGeneration => {
        const match = sbRows.find((sb) => sb.script_id === row.id) || null;
        return {
          id: row.id,
          project_id: row.project_id,
          created_at: row.created_at || row.updated_at || new Date().toISOString(),
          storage: "api",
          llm_configured: row.model_info?.llm_configured === true,
          script: rowToScript(row),
          storyboard: match ? storyboardRowToAgent(match, []) : null,
        };
      })
      .sort((a, b) => b.created_at.localeCompare(a.created_at));
  } catch (error) {
    // A backend outage must not erase the local copies the user already has.
    const local = readLocal(projectId || "default");
    if (local.length) return local;
    throw error;
  }
}

export async function deleteGeneration(projectId: string | null | undefined, id: string): Promise<void> {
  if (resolveStorage(projectId) === "local") {
    const owner = projectId || "default";
    writeLocal(readLocal(owner).filter((item) => item.id !== id));
    return;
  }
  await apiFetch(`/api/v1/scripts/${id}`, { method: "DELETE" });
}

/** Merge two saved stories of the same project without duplicating ids. */
export function mergeGenerations(primary: SavedGeneration[], secondary: SavedGeneration[]): SavedGeneration[] {
  const seen = new Set(primary.map((item) => item.id));
  const merged = [...primary];
  for (const item of secondary) {
    if (!seen.has(item.id)) {
      merged.push(item);
      seen.add(item.id);
    }
  }
  return merged.sort((a, b) => b.created_at.localeCompare(a.created_at));
}
