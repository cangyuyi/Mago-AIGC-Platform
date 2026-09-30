"use client";

import { useState } from "react";
import { useParams } from "next/navigation";
import { ChevronRight, FileText, Film, Inbox, Sparkles, Wand2 } from "lucide-react";
import { ChatInterface } from "@/components/chat/chat-interface";
import { GeneratedScriptOutput, GeneratedStoryboardOutput } from "@/components/artifacts/output-cards";
import { SavedOutputs } from "@/components/artifacts/saved-outputs";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { hasStoryboardContent, type AgentScript, type AgentStoryboard } from "@/lib/agent-output";
import { cn } from "@/lib/utils";

type StudioTab = "ideate" | "script" | "storyboard" | "library";

export default function StudioPage() {
  const params = useParams();
  const projectId = params.projectId as string;
  const [activeTab, setActiveTab] = useState<StudioTab>("ideate");
  const [scriptData, setScriptData] = useState<AgentScript | null>(null);
  const [storyboardData, setStoryboardData] = useState<AgentStoryboard | null>(null);
  const [savedCount, setSavedCount] = useState(0);

  return (
    <div className="flex h-screen flex-col bg-[#f5f5f7]">
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-black/[0.06] bg-white px-6 py-3">
        <div className="flex items-center gap-3">
          <h2 className="text-[17px] font-semibold tracking-[-0.01em] text-[#1d1d1f]">脚本创作中心</h2>
          <Badge variant="outline" className="border-black/[0.08] text-[#6e6e73]">项目 {projectId.slice(0, 8)}</Badge>
        </div>
        <div className="flex items-center gap-1 rounded-full border border-black/[0.06] bg-[#f5f5f7] p-1">
          <TabButton active={activeTab === "ideate"} onClick={() => setActiveTab("ideate")} icon={<Sparkles className="h-3.5 w-3.5" />} label="灵感" />
          <ChevronRight className="h-3 w-3 text-[#aeaeb2]" />
          <TabButton active={activeTab === "script"} onClick={() => setActiveTab("script")} icon={<FileText className="h-3.5 w-3.5" />} label="脚本" disabled={!scriptData} />
          <ChevronRight className="h-3 w-3 text-[#aeaeb2]" />
          <TabButton active={activeTab === "storyboard"} onClick={() => setActiveTab("storyboard")} icon={<Film className="h-3.5 w-3.5" />} label="分镜" disabled={!hasStoryboardContent(storyboardData)} />
          <ChevronRight className="h-3 w-3 text-[#aeaeb2]" />
          <TabButton active={activeTab === "library"} onClick={() => setActiveTab("library")} icon={<Inbox className="h-3.5 w-3.5" />} label={`成果库${savedCount ? ` ${savedCount}` : ""}`} />
        </div>
      </div>

      <div className="min-h-0 flex-1 overflow-hidden">
        <div className={cn("h-full", activeTab === "ideate" ? "block" : "hidden")}>
          <ChatInterface
            projectId={projectId}
            onScriptGenerated={(script) => { setScriptData(script); setActiveTab("script"); }}
            onStoryboardGenerated={(sb) => { setStoryboardData(sb); setActiveTab("storyboard"); }}
            onSaved={() => setSavedCount((n) => n + 1)}
            mode="detailed"
          />
        </div>

        {activeTab === "script" && scriptData && (
          <div className="h-full overflow-y-auto px-5 py-6 sm:px-7">
            <div className="mx-auto max-w-4xl">
              <GeneratedScriptOutput script={scriptData} />
              <div className="mt-4 flex justify-end">
                <Button variant="primary" className="gap-2" onClick={() => setActiveTab("storyboard")} disabled={!hasStoryboardContent(storyboardData)}>
                  <Wand2 className="h-4 w-4" />
                  查看分镜表
                </Button>
              </div>
            </div>
          </div>
        )}

        {activeTab === "storyboard" && storyboardData && (
          <div className="h-full overflow-y-auto px-5 py-6 sm:px-7">
            <div className="mx-auto max-w-4xl"><GeneratedStoryboardOutput storyboard={storyboardData} script={scriptData} projectId={projectId} /></div>
          </div>
        )}

        {activeTab === "library" && <SavedOutputs projectId={projectId} refreshKey={savedCount} />}

        {activeTab === "script" && !scriptData && <EmptyHint text="请先在灵感页完成创意发散" />}
        {activeTab === "storyboard" && !hasStoryboardContent(storyboardData) && <EmptyHint text="请先完成脚本并生成分镜表" />}
      </div>
    </div>
  );
}

function EmptyHint({ text }: { text: string }) {
  return <div className="flex h-full items-center justify-center text-sm text-[#86868b]">{text}</div>;
}

function TabButton({ active, onClick, icon, label, disabled }: {
  active: boolean; onClick: () => void; icon: React.ReactNode; label: string; disabled?: boolean;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled}
      className={cn(
        "flex items-center gap-1.5 rounded-full px-3.5 py-1.5 text-xs font-medium transition-all disabled:opacity-40",
        active ? "bg-white text-[#1d1d1f] shadow-apple-sm" : "text-[#6e6e73] hover:text-[#1d1d1f]"
      )}
    >
      {icon}
      {label}
    </button>
  );
}
