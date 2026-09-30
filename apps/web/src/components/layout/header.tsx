"use client";

import { useEffect, useState } from "react";
import { Bell, Search, Command } from "lucide-react";
import { Input } from "@/components/ui/input";

export function Header() {
  const [today, setToday] = useState("");

  useEffect(() => {
    setToday(new Intl.DateTimeFormat("zh-CN", { weekday: "long", month: "numeric", day: "numeric" }).format(new Date()));
  }, []);

  return (
    <header className="flex h-[76px] shrink-0 items-center gap-4 border-b border-black/[0.055] bg-[#f5f5f7]/80 px-5 backdrop-blur-2xl sm:px-7">
      <div className="flex-1">
        <div className="relative max-w-[420px]">
          <Search className="pointer-events-none absolute left-3.5 top-1/2 h-4 w-4 -translate-y-1/2 text-[#86868b]" strokeWidth={2} />
          <Input placeholder="搜索项目、创意、模板" className="h-10 rounded-[11px] border border-black/[0.04] bg-white/80 pl-10 pr-12 text-[13px] shadow-[0_1px_3px_rgba(0,0,0,0.035)] placeholder:text-[#98989d] focus-visible:ring-2 focus-visible:ring-[#007aff]/20" />
          <span className="pointer-events-none absolute right-3 top-1/2 flex -translate-y-1/2 items-center gap-0.5 rounded-md bg-black/[0.045] px-1.5 py-1 text-[10px] font-medium text-[#86868b]"><Command className="h-3 w-3" />K</span>
        </div>
      </div>
      <button type="button" aria-label="通知" className="relative flex h-10 w-10 items-center justify-center rounded-[11px] text-[#6e6e73] transition-colors hover:bg-white hover:text-[#1d1d1f] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#007aff]/30">
        <Bell className="h-[18px] w-[18px]" strokeWidth={1.9} />
        <span className="absolute right-2.5 top-2 h-1.5 w-1.5 rounded-full bg-[#ff3b30] ring-2 ring-[#f5f5f7]" />
      </button>
      <div className="hidden h-8 w-px bg-black/[0.08] sm:block" />
      <div className="hidden text-right sm:block"><div className="text-[12px] font-medium text-[#1d1d1f]">{today || "今天"}</div><div className="text-[11px] text-[#86868b]">准备好开始创作了吗？</div></div>
    </header>
  );
}
