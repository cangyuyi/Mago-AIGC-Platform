"use client";

import { useState } from "react";
import { useParams } from "next/navigation";
import { CheckCircle, Inbox, Sparkles } from "lucide-react";
import { ChatInterface } from "@/components/chat/chat-interface";
import { SavedOutputs } from "@/components/artifacts/saved-outputs";
import { cn } from "@/lib/utils";

type Tab = "chat" | "library";

export default function ProjectDetailPage() {
  const params = useParams();
  const projectId = params.id as string;
  const [tab, setTab] = useState<Tab>("chat");
  const [savedCount, setSavedCount] = useState(0);

  return (
    <div className="flex h-screen flex-col bg-[#f5f5f7]">
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-black/[0.06] bg-white px-6 py-3">
        <div>
          <h2 className="font-semibold tracking-[-0.01em] text-[#1d1d1f]">项目创作</h2>
          <p className="mt-0.5 text-xs text-[#6e6e73]">输入需求后，直接得到完整脚本、节拍和分镜表</p>
        </div>

        <div className="flex items-center gap-1 rounded-full border border-black/[0.06] bg-[#f5f5f7] p-1">
          <TabButton active={tab === "chat"} onClick={() => setTab("chat")} icon={<Sparkles className="h-3.5 w-3.5" />} label="对话" />
          <TabButton active={tab === "library"} onClick={() => setTab("library")} icon={<Inbox className="h-3.5 w-3.5" />} label={`成果库${savedCount ? ` ${savedCount}` : ""}`} />
        </div>

        <span className="hidden items-center gap-1.5 rounded-full border border-black/[0.08] bg-[#f5f5f7] px-2.5 py-1 text-xs text-[#6e6e73] sm:inline-flex">
          <CheckCircle className="h-3 w-3 text-[#34c759]" />项目 {projectId.slice(0, 8)}…
        </span>
      </div>

      <div className="min-h-0 flex-1 overflow-hidden">
        {/* Both panes stay mounted so switching tabs never loses the chat. */}
        <div className={cn("h-full", tab === "chat" ? "block" : "hidden")}>
          <ChatInterface projectId={projectId} mode="quick" onSaved={() => setSavedCount((n) => n + 1)} />
        </div>
        <div className={cn("h-full overflow-hidden", tab === "library" ? "block" : "hidden")}>
          <SavedOutputs projectId={projectId} refreshKey={savedCount} />
        </div>
      </div>
    </div>
  );
}

function TabButton({ active, onClick, icon, label }: { active: boolean; onClick: () => void; icon: React.ReactNode; label: string }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={cn(
        "flex items-center gap-1.5 rounded-full px-3.5 py-1.5 text-xs font-medium transition-all",
        active ? "bg-white text-[#1d1d1f] shadow-apple-sm" : "text-[#6e6e73] hover:text-[#1d1d1f]"
      )}
    >
      {icon}
      {label}
    </button>
  );
}
