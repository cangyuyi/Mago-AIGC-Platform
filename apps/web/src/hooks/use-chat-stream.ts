"use client";
import { useCallback, useRef, useState } from "react";
import { fetchWithAuth } from "@/lib/auth";
import { SSEParser } from "@/lib/sse";

interface StreamOptions {
  onChunk?: (text: string) => void;
  onThinking?: (text: string) => void;
  onIdeas?: (ideas: any[]) => void;
  onScript?: (script: any) => void;
  onStoryboard?: (sb: any) => void;
  onEval?: (eval_: any) => void;
  onCompliance?: (comp: any) => void;
  onDone?: (state: any) => void;
  onError?: (err: string) => void;
}

function responseError(response: Response, body: string): Error {
  try {
    const data = JSON.parse(body) as { message?: string; detail?: string; error?: string };
    return new Error(data.message || data.detail || data.error || `请求失败（HTTP ${response.status}）`);
  } catch {
    return new Error(`请求失败（HTTP ${response.status}）`);
  }
}

export function useChatStream() {
  const [isStreaming, setIsStreaming] = useState(false);
  const [currentStep, setCurrentStep] = useState("");
  const abortRef = useRef<AbortController | null>(null);

  const stop = useCallback(() => {
    abortRef.current?.abort();
    setIsStreaming(false);
  }, []);

  const send = useCallback(async (message: string, opts: {
    projectId?: string; mode?: string; selectedIdeaId?: string; feedback?: string;
  } & StreamOptions) => {
    setIsStreaming(true);
    abortRef.current = new AbortController();

    try {
      const resp = await fetchWithAuth("/api/agent/run", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          message, project_id: opts.projectId,
          mode: opts.mode || "detailed",
          selected_idea_id: opts.selectedIdeaId,
          feedback: opts.feedback,
        }),
        signal: abortRef.current.signal,
      });
      if (!resp.ok) throw responseError(resp, await resp.text());
      const reader = resp.body?.getReader();
      if (!reader) throw new Error("服务端未返回可读取的流");
      const decoder = new TextDecoder();
      const parser = new SSEParser();
      let accumulatedContent = "";
      let ideas: any[] = [];
      let script: any = null;
      let storyboard: any = null;

      const handleEvent = (eventName: string, rawData: string) => {
        if (rawData === "[DONE]") return;
        const data = JSON.parse(rawData) as any;
        if (eventName === "error") throw new Error(data?.message || "Agent 执行失败");
        if (eventName === "thinking" && data?.text) {
          setCurrentStep(data.text); opts.onThinking?.(data.text);
        } else if (eventName === "chunk" && data?.text) {
          accumulatedContent += data.text; opts.onChunk?.(data.text);
        } else if (eventName === "ideas" && data?.ideas) {
          ideas = data.ideas; opts.onIdeas?.(ideas);
        } else if (eventName === "script" && data?.script) {
          script = data.script; opts.onScript?.(script);
        } else if (eventName === "storyboard" && data?.storyboard) {
          storyboard = data.storyboard; opts.onStoryboard?.(storyboard);
        } else if (eventName === "eval" && data?.evaluation) {
          opts.onEval?.(data.evaluation);
        } else if (eventName === "compliance" && data?.compliance) {
          opts.onCompliance?.(data.compliance);
        } else if (eventName === "done") {
          opts.onDone?.({ content: accumulatedContent, ideas, script, storyboard, state: data?.state });
        }
      };

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        parser.feed(decoder.decode(value, { stream: true }), handleEvent);
      }
      parser.feed(decoder.decode(), handleEvent);
      parser.end(handleEvent);
    } catch (e: any) {
      if (e.name !== "AbortError") opts.onError?.(e.message || String(e));
    } finally {
      setIsStreaming(false);
      setCurrentStep("");
      abortRef.current = null;
    }
  }, []);

  return { send, stop, isStreaming, currentStep };
}
