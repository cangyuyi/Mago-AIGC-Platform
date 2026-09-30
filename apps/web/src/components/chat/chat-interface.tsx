"use client";

import { useState, useRef, useEffect, useCallback } from "react";
import {
  Send,
  Sparkles,
  Loader2,
  Lightbulb,
  CheckCircle,
  Square,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { fetchWithAuth } from "@/lib/auth";
import { SSEParser } from "@/lib/sse";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import {
  hasScriptContent,
  hasStoryboardContent,
  type AgentScript,
  type AgentStoryboard,
} from "@/lib/agent-output";
import { resolveStorage, saveGeneration, type GenerationProvenance, type SavedGeneration } from "@/lib/artifacts";
import {
  GeneratedScriptOutput,
  GeneratedStoryboardOutput,
  SaveStatusChip,
  type SaveState,
} from "@/components/artifacts/output-cards";

interface Message {
  id: string;
  role: "user" | "assistant" | "thinking";
  content: string;
  ideas?: CreativeIdea[];
  script?: AgentScript;
  storyboard?: AgentStoryboard;
  /** Provenance of the streamed answer: false means an offline template. */
  llmConfigured?: boolean;
  model?: string;
  save?: SaveState;
}

interface CreativeIdea {
  id: string;
  title: string;
  description: string;
  hook_direction?: string;
  emotion_tone?: string;
  differentiation?: string;
  ai_feasibility_score?: number;
  difficulty?: string;
  estimated_duration?: number;
  tags?: string[];
  is_hot_trend?: boolean;
}

interface SseEvent {
  text?: string;
  ideas?: CreativeIdea[];
  script?: AgentScript;
  storyboard?: AgentStoryboard;
  llm_configured?: boolean;
  model?: string;
  message?: string;
}

/** A human-in-the-loop gate the workflow paused at, asking for a decision. */
interface PendingGate {
  gate: string;
  prompt: string;
  payload?: Record<string, unknown>;
}

interface DoneState {
  hitl_required?: boolean;
  hitl_node?: string;
  hitl_prompt?: string;
  hitl_payload?: Record<string, unknown>;
}

interface ChatInterfaceProps {
  projectId?: string;
  initialMessage?: string;
  onIdeaSelect?: (idea: CreativeIdea) => void;
  onScriptGenerated?: (script: AgentScript) => void;
  onStoryboardGenerated?: (storyboard: AgentStoryboard) => void;
  /** Fired after a generation is durably stored, so sibling panels can refresh. */
  onSaved?: (generation: SavedGeneration) => void;
  mode?: "ideation" | "quick" | "detailed";
}

export function ChatInterface({
  projectId,
  initialMessage,
  onIdeaSelect,
  onScriptGenerated,
  onStoryboardGenerated,
  onSaved,
  mode = "detailed",
}: ChatInterfaceProps) {
  const [messages, setMessages] = useState<Message[]>([
    {
      id: "welcome",
      role: "assistant",
      content:
        "你好！我是 Mago 创意助手。\n\n告诉我你想做什么类型的视频？哪怕只有一个词，我也能帮你发散出10个创意方向。\n\n比如：\n- 「美妆口红种草」\n- 「职场搞笑短剧」\n- 「iPhone开箱」\n- 或者直接点「🎲随机灵感」试试手气！",
    },
  ]);
  const [input, setInput] = useState(initialMessage || "");
  const [isStreaming, setIsStreaming] = useState(false);
  const [currentStep, setCurrentStep] = useState("");
  const [selectedIdeaId, setSelectedIdeaId] = useState<string | null>(null);
  // The gate the workflow is waiting on, if any. Cleared on resume.
  const [pendingGate, setPendingGate] = useState<PendingGate | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const abortRef = useRef<AbortController | null>(null);

  const scrollToBottom = useCallback(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, []);

  useEffect(() => { scrollToBottom(); }, [messages, scrollToBottom]);

  useEffect(() => () => {
    abortRef.current?.abort();
  }, []);

  const quickSuggestions = ["🎲 随机灵感", "💄 美妆种草", "📱 数码开箱", "🍜 美食探店", "💼 职场知识", "⚡ 快速出脚本"];

  async function handleSend(
    customMessage?: string,
    overrideMode?: string,
    overrideIdeaId?: string,
    resumeValue?: unknown,
  ) {
    const messageText = customMessage || input.trim();
    if (!messageText || isStreaming) return;

    const sendMode = overrideMode || mode;
    const isResume = resumeValue !== undefined;
    const userMsg: Message = { id: `user-${Date.now()}`, role: "user", content: messageText };
    setMessages((prev) => [...prev, userMsg]);
    setInput("");
    setIsStreaming(true);
    const controller = new AbortController();
    abortRef.current = controller;

    const thinkingId = `thinking-${Date.now()}`;
    const assistantMsgId = `assistant-${Date.now()}`;
    setMessages((prev) => [...prev,
      { id: thinkingId, role: "thinking", content: "正在思考..." },
      { id: assistantMsgId, role: "assistant", content: "" },
    ]);
    if (isResume) setPendingGate(null);

    try {
      const response = await fetchWithAuth("/api/agent/run", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          message: messageText,
          project_id: projectId,
          mode: sendMode,
          // A gate response resumes the paused checkpoint; a fresh turn starts
          // over and may carry an explicit idea selection.
          resume: isResume ? resumeValue : undefined,
          selected_idea_id: isResume ? undefined : (overrideIdeaId || selectedIdeaId || undefined),
          history: messages.filter((m) => m.role === "user" || m.role === "assistant").map((m) => ({ role: m.role, content: m.content })),
        }),
        signal: controller.signal,
      });

      if (!response.ok) {
        const text = await response.text();
        let message = `请求失败（HTTP ${response.status}）`;
        try {
          const data = JSON.parse(text) as { message?: string; detail?: string; error?: string };
          message = data.message || data.detail || data.error || message;
        } catch { /* use HTTP fallback */ }
        throw new Error(message);
      }
      const reader = response.body?.getReader();
      if (!reader) throw new Error("服务端未返回可读取的流");
      const decoder = new TextDecoder();
      const parser = new SSEParser();
      let accumulatedContent = "";
      let ideas: CreativeIdea[] = [];
      let script: AgentScript | null = null;
      let storyboard: AgentStoryboard | null = null;
      let provenance: GenerationProvenance = {};

      const handleEvent = (eventName: string, rawData: string) => {
        if (rawData === "[DONE]") return;
        const data = JSON.parse(rawData) as SseEvent;
        if (eventName === "error") {
          throw new Error(`__STREAM_ERROR__${data?.message || "Agent 执行失败"}`);
        } else if (eventName === "meta") {
          provenance = { llm_configured: data?.llm_configured, model: data?.model };
        } else if (eventName === "thinking" && data?.text) {
          setCurrentStep(data.text);
        } else if (eventName === "chunk" && data?.text) {
          accumulatedContent += data.text;
          setMessages((prev) => prev.map((m) => m.id === assistantMsgId ? { ...m, content: accumulatedContent } : m));
        } else if (eventName === "ideas" && data?.ideas) {
          ideas = data.ideas;
          setMessages((prev) => prev.map((m) => m.id === assistantMsgId ? { ...m, ideas } : m));
        } else if (eventName === "script" && data?.script) {
          script = data.script;
          if (typeof data.llm_configured === "boolean") provenance = { llm_configured: data.llm_configured, model: data.model };
          setMessages((prev) => prev.map((m) => (m.id === assistantMsgId ? { ...m, script: script ?? undefined, llmConfigured: provenance.llm_configured, model: provenance.model } : m)));
        } else if (eventName === "storyboard" && data?.storyboard) {
          storyboard = data.storyboard;
          if (typeof data.llm_configured === "boolean") provenance = { llm_configured: data.llm_configured, model: data.model };
          setMessages((prev) => prev.map((m) => (m.id === assistantMsgId ? { ...m, storyboard: storyboard ?? undefined, llmConfigured: provenance.llm_configured, model: provenance.model } : m)));
        } else if (eventName === "done") {
          // The workflow may have paused for a human decision. Surface the gate
          // so the next turn resumes the checkpoint instead of starting over.
          const state = (data as { state?: DoneState })?.state;
          if (state?.hitl_required && state.hitl_node) {
            setPendingGate({
              gate: state.hitl_node,
              prompt: state.hitl_prompt || "需要你的确认后继续",
              payload: state.hitl_payload || {},
            });
          } else {
            setPendingGate(null);
          }
        }
      };

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        parser.feed(decoder.decode(value, { stream: true }), handleEvent);
      }
      parser.feed(decoder.decode(), handleEvent);
      parser.end(handleEvent);

      setMessages((prev) => prev.filter((m) => m.id !== thinkingId));
      setCurrentStep("");

      if (script && onScriptGenerated) onScriptGenerated(script);
      if (storyboard && onStoryboardGenerated) onStoryboardGenerated(storyboard);

      // A generation that only lives in React state disappears on refresh, so
      // store it before telling the user anything about success.
      if (hasScriptContent(script) || hasStoryboardContent(storyboard)) {
        await persistGeneration(assistantMsgId, { script, storyboard }, provenance);
      }
    } catch (e) {
      setMessages((prev) => prev.filter((m) => m.id !== thinkingId));
      if (e instanceof Error && e.name === "AbortError") {
        setMessages((prev) => prev.map((m) =>
          m.id === assistantMsgId && !m.content.trim() ? { ...m, content: "已停止生成。" } : m,
        ));
      } else {
        const reason = e instanceof Error ? e.message : String(e);
        setMessages((prev) => prev.map((m) => m.id === assistantMsgId ? { ...m, content: "出错了: " + reason } : m));
      }
    } finally {
      setCurrentStep("");
      setIsStreaming(false);
      if (abortRef.current === controller) abortRef.current = null;
    }
  }

  /** Store a finished generation and reflect the outcome on that message. */
  async function persistGeneration(
    messageId: string,
    payload: { script: AgentScript | null; storyboard: AgentStoryboard | null },
    provenance: GenerationProvenance,
  ) {
    setMessages((prev) => prev.map((m) => (m.id === messageId ? { ...m, save: { state: "saving" } } : m)));
    try {
      const saved = await saveGeneration(projectId, payload, provenance);
      setMessages((prev) => prev.map((m) => (m.id === messageId ? { ...m, save: { state: "saved", storage: saved.storage } } : m)));
      if (onSaved) onSaved(saved);
    } catch (error) {
      const reason = error instanceof Error ? error.message : String(error);
      setMessages((prev) => prev.map((m) => (m.id === messageId ? { ...m, save: { state: "error", error: reason } } : m)));
    }
  }

  function stopStreaming() {
    abortRef.current?.abort();
  }

  async function selectIdea(idea: CreativeIdea) {
    setSelectedIdeaId(idea.id);
    if (onIdeaSelect) onIdeaSelect(idea);
    // If the workflow is paused at the idea gate, resume the checkpoint with the
    // choice. Otherwise start a fresh run carrying the selection.
    const resuming = pendingGate?.gate === "idea_selection";
    await handleSend(
      `我选这个方向：${idea.title}。${idea.description} 请帮我写创意简报、设计钩子、写完整脚本。`,
      resuming ? mode : "quick",
      idea.id,
      resuming ? { selected_idea_id: idea.id } : undefined,
    );
  }

  /** Approve the current gate and continue the paused run. */
  async function approveGate() {
    if (!pendingGate) return;
    await handleSend("确认，继续。", mode, undefined, { approved: true });
  }

  /** Send edits/feedback for the current gate, which resumes with the note. */
  async function sendGateFeedback(feedback: string) {
    if (!pendingGate || !feedback.trim()) return;
    await handleSend(feedback, mode, undefined, { approved: true, feedback });
  }

  /** Reject the current step so the workflow can revise it. */
  async function rejectGate() {
    if (!pendingGate) return;
    await handleSend("这一步需要修改，请根据反馈调整。", mode, undefined, { approved: false });
  }

  function handleKeyDown(e: React.KeyboardEvent) {
    if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); handleSend(); }
  }

  return (
    <div className="flex h-full flex-col bg-white">
      <div className="flex-1 overflow-y-auto px-5 py-5 sm:px-7 sm:py-6">
        {currentStep && isStreaming && (
          <div className="mx-auto mb-4 flex max-w-4xl items-center gap-2 rounded-[12px] border border-[#007aff]/10 bg-[#f5f9ff] px-3 py-2 text-xs text-[#6e6e73]"><Loader2 className="h-3.5 w-3.5 animate-spin text-[#007aff]" />{currentStep}</div>
        )}
        {messages.map((message) => (
          <div key={message.id} className={cn("mx-auto mb-6 flex max-w-4xl", message.role === "user" ? "justify-end" : "justify-start")}>
            {message.role === "thinking" ? (
              <div className="flex items-center gap-2 px-3 py-2 text-sm text-[#86868b]"><Loader2 className="h-3.5 w-3.5 animate-spin text-[#007aff]" />{message.content}</div>
            ) : message.role === "user" ? (
              <div className="max-w-[78%] rounded-[18px] rounded-br-[6px] bg-[#007aff] px-4 py-3 text-[14px] leading-relaxed text-white shadow-[0_2px_6px_rgba(0,122,255,0.16)]">{message.content}</div>
            ) : (
              <div className="flex w-full max-w-[94%] items-start gap-3">
                <div className="mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-[9px] bg-[#e8f2ff] text-[#007aff]"><Sparkles className="h-3.5 w-3.5" /></div>
                <div className="min-w-0 flex-1">
                  {message.content && (
                    <div className="rounded-[18px] rounded-tl-[6px] bg-[#f5f5f7] px-5 py-4 text-[14px] leading-relaxed text-[#1d1d1f] prose prose-sm max-w-none prose-headings:font-semibold prose-p:my-2 prose-ul:my-2">
                      <ReactMarkdown remarkPlugins={[remarkGfm]}>{message.content}</ReactMarkdown>
                    </div>
                  )}
                  {message.ideas && message.ideas.length > 0 && (
                    <div className="mt-3 grid grid-cols-1 gap-3 md:grid-cols-2">
                      {message.ideas.map((idea) => (
                        <Card key={idea.id} className={cn("group cursor-pointer rounded-[18px] border-black/[0.06] p-4 transition-shadow hover:shadow-apple-lg", selectedIdeaId === idea.id && "ring-2 ring-[#007aff]/30")}>
                          <div className="mb-2 flex items-start justify-between gap-2">
                            <h4 className="text-sm font-semibold">{idea.title}</h4>
                            {idea.is_hot_trend && <Badge variant="danger">🔥热点</Badge>}
                          </div>
                          <p className="mb-2 line-clamp-3 text-xs text-muted-foreground">{idea.description}</p>
                          {idea.hook_direction && <p className="mb-2 text-xs text-primary">💡 {idea.hook_direction}</p>}
                          <div className="mb-3 flex flex-wrap items-center gap-1.5">
                            {idea.emotion_tone && <Badge variant="outline" className="text-xs">{idea.emotion_tone}</Badge>}
                            {idea.difficulty && <Badge variant={idea.difficulty === "low" ? "success" : idea.difficulty === "high" ? "danger" : "warning"} className="text-xs">{idea.difficulty === "low" ? "易制作" : idea.difficulty === "medium" ? "中等" : "较难"}</Badge>}
                            {idea.estimated_duration && <Badge variant="outline" className="text-xs">{idea.estimated_duration}s</Badge>}
                            {typeof idea.ai_feasibility_score === "number" && <Badge variant={idea.ai_feasibility_score >= 7 ? "success" : "warning"} className="text-xs">AI可行 {idea.ai_feasibility_score}/10</Badge>}
                          </div>
                          <Button size="sm" variant="primary" className="w-full gap-1 text-xs" onClick={() => selectIdea(idea)} disabled={isStreaming}>
                            <CheckCircle className="h-3 w-3" />
                            用这个写脚本
                          </Button>
                        </Card>
                      ))}
                    </div>
                  )}
                  {message.script && <GeneratedScriptOutput script={message.script} />}
                  {message.storyboard && (
                    <GeneratedStoryboardOutput
                      storyboard={message.storyboard}
                      script={message.script}
                      projectId={projectId}
                    />
                  )}
                  {(message.save || message.llmConfigured === false) && (
                    <SaveStatusChip
                      save={message.save}
                      llmConfigured={message.llmConfigured}
                      model={message.model}
                      storage={resolveStorage(projectId)}
                    />
                  )}
                </div>
              </div>
            )}
          </div>
        ))}
        <div ref={messagesEndRef} />
      </div>

      <div className="border-t border-black/[0.05] bg-white px-5 pb-4 pt-4 sm:px-7">
        {pendingGate && (
          <div className="mb-3 mx-auto max-w-4xl rounded-[14px] border border-[#ff9f0a]/30 bg-[#fff8ec] px-4 py-3">
            <div className="mb-2 flex items-center gap-2 text-[13px] font-medium text-[#8a5a00]">
              <CheckCircle className="h-4 w-4 text-[#ff9f0a]" />
              <span>{gateLabel(pendingGate.gate)}</span>
            </div>
            <p className="mb-3 text-xs text-[#8a5a00]/90">{pendingGate.prompt}</p>
            {pendingGate.gate === "idea_selection" && pendingGate.payload?.ideas ? (
              <p className="text-xs text-[#8a5a00]/80">请在上方创意卡片中选择一个方向继续。</p>
            ) : (
              <div className="flex flex-wrap items-center gap-2">
                <Button size="sm" variant="primary" className="gap-1 text-xs" onClick={approveGate} disabled={isStreaming}>
                  <CheckCircle className="h-3.5 w-3.5" />确认并继续
                </Button>
                <Button size="sm" variant="secondary" className="gap-1 text-xs" onClick={rejectGate} disabled={isStreaming}>
                  需要修改
                </Button>
                <button
                  type="button"
                  onClick={() => {
                    const note = window.prompt("请说明需要调整的地方：");
                    if (note) void sendGateFeedback(note);
                  }}
                  disabled={isStreaming}
                  className="text-xs text-[#8a5a00] underline underline-offset-2 disabled:opacity-50">
                  附上修改意见
                </button>
              </div>
            )}
          </div>
        )}
        {messages.length <= 1 && (
          <div className="mb-3 flex gap-2 overflow-x-auto pb-1">
            {quickSuggestions.map((s) => (
              <button key={s}
                onClick={() => handleSend(
                  s === "🎲 随机灵感" ? "给我一些随机的创意灵感，什么类型都可以" :
                  s === "⚡ 快速出脚本" ? "帮我快速生成一个短视频脚本" :
                  s.replace(/[💄📱🍜💼⚡]/g, "").trim() + "视频创意",
                  s === "⚡ 快速出脚本" ? "quick" : undefined,
                )}
                disabled={isStreaming}
                className="flex shrink-0 items-center gap-1.5 rounded-full border border-black/[0.08] bg-[#f5f5f7] px-3 py-1.5 text-xs text-[#515154] transition-colors hover:bg-[#e9e9ed] disabled:opacity-50">
                <Lightbulb className="h-3 w-3 text-[#86868b]" />{s}
              </button>
            ))}
          </div>
        )}
        <div className="flex items-end gap-3">
          <div className="relative flex-1">
            <textarea ref={inputRef} value={input} onChange={(e) => setInput(e.target.value)} onKeyDown={handleKeyDown}
              placeholder="描述你想做的视频…（Enter 发送，Shift + Enter 换行）" rows={1}
              className="w-full resize-none rounded-[17px] border border-black/[0.08] bg-[#f5f5f7] px-4 py-3 pr-12 text-[14px] text-[#1d1d1f] placeholder:text-[#98989d] focus:outline-none focus:ring-2 focus:ring-[#007aff]/20"
              style={{ minHeight: "48px", maxHeight: "200px" }} disabled={isStreaming} />
          </div>
          <Button
            onClick={isStreaming ? stopStreaming : () => handleSend()}
            disabled={!isStreaming && !input.trim()}
            variant={isStreaming ? "secondary" : "primary"}
            size="default"
            className="h-12 w-12 shrink-0 rounded-full p-0"
            aria-label={isStreaming ? "停止生成" : "发送消息"}
            title={isStreaming ? "停止生成" : "发送消息"}
          >
            {isStreaming ? <Square className="h-4 w-4 fill-current" /> : <Send className="h-5 w-5" />}
          </Button>
        </div>
        <p className="mt-2 text-center text-[10px] text-[#98989d]">Mago 创意助手 · 内容由 AI 生成，请在发布前确认</p>
      </div>
    </div>
  );
}

/** Human-readable label for a workflow gate identifier. */
function gateLabel(gate: string): string {
  switch (gate) {
    case "idea_selection":
      return "请选择一个创意方向";
    case "brief_review":
      return "请确认创意简报";
    case "script_review":
      return "请确认脚本";
    case "storyboard_review":
      return "请确认分镜";
    default:
      return "等待你的确认";
  }
}
