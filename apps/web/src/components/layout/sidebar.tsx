"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";
import {
  Sparkles,
  LayoutDashboard,
  FolderOpen,
  TrendingUp,
  BookOpen,
  User,
  Settings,
  Film,
  Lightbulb,
  Wand2,
  Palette,
  Download,
} from "lucide-react";

const navItems = [
  { href: "/dashboard", label: "工作台", icon: LayoutDashboard },
  { href: "/projects", label: "我的项目", icon: FolderOpen },
  { href: "/studio", label: "脚本创作", icon: Wand2, badge: "03" },
  { href: "/characters", label: "角色管理", icon: User, badge: "04" },
  { href: "/styles", label: "风格预设", icon: Palette, badge: "04" },
  { href: "/prompts", label: "提示词导出", icon: Download, badge: "05" },
  { href: "/trends", label: "热点灵感", icon: TrendingUp },
  { href: "/topics", label: "AI选题", icon: Lightbulb },
  { href: "/viral", label: "爆款拆解", icon: Film },
  { href: "/knowledge", label: "知识库", icon: BookOpen },
];

export function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="flex h-screen w-[244px] shrink-0 flex-col border-r border-black/[0.06] bg-[#f6f6f8]/92 backdrop-blur-2xl">
      <div className="flex h-[76px] items-center border-b border-black/[0.05] px-5">
        <Link href="/dashboard" className="flex items-center gap-3 rounded-xl outline-none focus-visible:ring-2 focus-visible:ring-[#007aff]/30">
          <div className="flex h-9 w-9 items-center justify-center rounded-[11px] bg-[#007aff] text-white shadow-[0_2px_6px_rgba(0,122,255,0.22)]">
            <Sparkles className="h-[18px] w-[18px]" strokeWidth={2.2} />
          </div>
          <div>
            <div className="text-[17px] font-semibold tracking-[-0.035em] text-[#1d1d1f]">Mago</div>
            <div className="text-[10px] font-medium uppercase tracking-[0.12em] text-[#86868b]">Creative OS</div>
          </div>
        </Link>
      </div>

      <nav className="flex-1 overflow-y-auto px-2 py-4" aria-label="主导航">
        <p className="px-3 pb-2 text-[10px] font-semibold uppercase tracking-[0.14em] text-[#86868b]">Workspace</p>
        <div className="space-y-0.5">
          {navItems.map((item) => {
            const isActive = pathname === item.href || pathname.startsWith(`${item.href}/`);
            const Icon = item.icon;
            return (
              <Link
                key={item.href}
                href={item.href}
                aria-current={isActive ? "page" : undefined}
                className={cn(
                  "group flex items-center gap-3 rounded-[10px] px-3 py-2 text-[13px] font-medium transition-colors duration-150",
                  isActive
                    ? "bg-[#dbeeff] text-[#0066cc]"
                    : "text-[#515154] hover:bg-black/[0.045] hover:text-[#1d1d1f]",
                )}
              >
                <Icon className={cn("h-[17px] w-[17px]", isActive ? "text-[#007aff]" : "text-[#86868b] group-hover:text-[#1d1d1f]")} strokeWidth={1.9} />
                <span className="truncate">{item.label}</span>
                {item.badge && (
                  <span className={cn("ml-auto rounded-md px-1.5 py-0.5 text-[10px] font-semibold", isActive ? "bg-white/70 text-[#007aff]" : "bg-black/[0.05] text-[#86868b]")}>{item.badge}</span>
                )}
              </Link>
            );
          })}
        </div>
      </nav>

      <div className="border-t border-black/[0.05] p-3">
        <Link href="/settings" className="flex items-center gap-3 rounded-[10px] px-3 py-2 text-[13px] font-medium text-[#515154] transition-colors hover:bg-black/[0.045] hover:text-[#1d1d1f]">
          <Settings className="h-[17px] w-[17px] text-[#86868b]" strokeWidth={1.9} />设置
        </Link>
        <div className="mt-2 flex items-center gap-3 rounded-[14px] border border-black/[0.04] bg-white/75 px-3 py-2.5 shadow-[0_1px_2px_rgba(0,0,0,0.025)]">
          <div className="flex h-8 w-8 items-center justify-center rounded-full bg-[#e8f2ff] text-[#007aff]"><User className="h-4 w-4" /></div>
          <div className="min-w-0 text-[13px]">
            <div className="truncate font-medium text-[#1d1d1f]">我的工作区</div>
            <div className="text-[11px] text-[#86868b]">免费版</div>
          </div>
          <span className="ml-auto h-2 w-2 rounded-full bg-[#34c759]" aria-label="在线" />
        </div>
      </div>
    </aside>
  );
}
