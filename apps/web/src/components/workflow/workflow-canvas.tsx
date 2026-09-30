"use client";
import { useMemo } from "react";

type NodeStatus = "pending" | "running" | "waiting" | "done" | "error" | "skipped";
interface WorkflowNode {
  id: string;
  label: string;
  status: NodeStatus;
  icon: string;
}

const defaultNodes: WorkflowNode[] = [
  { id: "ideation", label: "灵感发散", status: "pending", icon: "💡" },
  { id: "brief", label: "创意简报", status: "pending", icon: "📋" },
  { id: "script", label: "脚本写作", status: "pending", icon: "📝" },
  { id: "storyboard", label: "分镜设计", status: "pending", icon: "🎬" },
  { id: "character", label: "角色绑定", status: "pending", icon: "👤" },
  { id: "style", label: "风格应用", status: "pending", icon: "🎨" },
  { id: "prompts", label: "提示词生成", status: "pending", icon: "✨" },
  { id: "export", label: "导出/Mago", status: "pending", icon: "🚀" },
];

const statusColors: Record<NodeStatus, { bg: string; border: string; text: string; icon: string }> = {
  pending: { bg: "bg-muted", border: "border-border", text: "text-muted-foreground", icon: "opacity-40" },
  running: { bg: "bg-blue-50 dark:bg-blue-950", border: "border-blue-400", text: "text-blue-600 dark:text-blue-400", icon: "animate-pulse" },
  waiting: { bg: "bg-yellow-50 dark:bg-yellow-950", border: "border-yellow-400", text: "text-yellow-600 dark:text-yellow-400", icon: "" },
  done: { bg: "bg-green-50 dark:bg-green-950", border: "border-green-400", text: "text-green-600 dark:text-green-400", icon: "" },
  error: { bg: "bg-red-50 dark:bg-red-950", border: "border-red-400", text: "text-red-600 dark:text-red-400", icon: "" },
  skipped: { bg: "bg-gray-50 dark:bg-gray-900", border: "border-gray-300", text: "text-gray-400", icon: "opacity-50" },
};

export function WorkflowCanvas({ currentStep, completedSteps = [], waitingForHuman = false }: {
  currentStep?: string; completedSteps?: string[]; waitingForHuman?: boolean;
}) {
  const nodes = useMemo(() => defaultNodes.map(n => {
    let status: NodeStatus = "pending";
    if (completedSteps.includes(n.id)) status = "done";
    if (currentStep && n.id === currentStep) status = waitingForHuman ? "waiting" : "running";
    return { ...n, status };
  }), [currentStep, completedSteps, waitingForHuman]);

  return (
    <div className="w-full overflow-x-auto py-2">
      <div className="flex items-center gap-1 min-w-max px-2">
        {nodes.map((node, i) => {
          const colors = statusColors[node.status];
          const isLast = i === nodes.length - 1;
          return (
            <div key={node.id} className="flex items-center">
              <div className={`flex flex-col items-center gap-1 p-2 rounded-lg border-2 ${colors.bg} ${colors.border} transition-all min-w-[70px]`}>
                <span className={`text-xl ${colors.icon}`}>{node.icon}</span>
                <span className={`text-[10px] font-medium ${colors.text} text-center leading-tight`}>{node.label}</span>
                {node.status === "waiting" && <span className="text-[9px] text-yellow-600 font-semibold">⏸等你</span>}
                {node.status === "running" && <span className="text-[9px] text-blue-600">⟳进行中</span>}
                {node.status === "done" && <span className="text-[9px]">✓</span>}
              </div>
              {!isLast && (
                <div className={`w-6 h-0.5 ${nodes[i+1].status !== "pending" || node.status === "done" ? "bg-green-400" : "bg-border"} mx-0.5`} />
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
