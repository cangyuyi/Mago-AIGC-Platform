"use client";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Plus, Palette, Eye, Trash2 } from "lucide-react";

const presetStyles = [
  { id: "s1", name: "电影感-青橙色调", category: "color_grading", colors: ["#FF8C00","#008B8B","#0D1B2A"], desc: "经典好莱坞电影调色，青橙互补色" },
  { id: "s2", name: "温暖金色", category: "color_grading", colors: ["#FFD700","#FF8C00","#FFF5E6"], desc: "黄金时刻光线，温馨治愈" },
  { id: "s3", name: "冷色霓虹赛博", category: "color_grading", colors: ["#00FFFF","#FF00FF","#0D0D1A"], desc: "赛博朋克霓虹灯光" },
  { id: "s4", name: "梦幻马卡龙", category: "color_grading", colors: ["#FFB6C1","#E6E6FA","#B0E0E6"], desc: " pastel柔和色调，甜美梦幻" },
  { id: "s5", name: "韩剧柔光", category: "cinematography", colors: ["#FFF0F5","#FFE4E1","#DDA0DD"], desc: "浪漫柔光，韩剧质感" },
  { id: "s6", name: "Wes Anderson", category: "director", colors: ["#F5DEB3","#FF6B6B","#4ECDC4"], desc: "对称构图+马卡龙色" },
];

const categories = ["全部","color_grading","lighting","visual_style","cinematography","director"];

export default function StylesPage() {
  const [activeCat, setActiveCat] = useState("全部");

  return (
    <div className="p-6 max-w-6xl mx-auto">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold flex items-center gap-2"><Palette className="w-6 h-6"/>风格预设</h1>
          <p className="text-sm text-muted-foreground mt-1">选择或创建视觉风格，统一视频调色/光影/镜头风格</p>
        </div>
        <Button className="gap-2"><Plus className="w-4 h-4"/>新建风格</Button>
      </div>

      <div className="flex gap-2 mb-6 overflow-x-auto pb-2">
        {categories.map(cat => (
          <button key={cat} onClick={()=>setActiveCat(cat)}
            className={"px-3 py-1.5 text-xs rounded-full border transition shrink-0 "+
              (activeCat===cat?"bg-primary text-primary-foreground border-primary":"border-border hover:bg-muted")}>
            {cat==="全部"?"全部":cat.replace("_"," ")}
          </button>
        ))}
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {presetStyles.map(s => (
          <Card key={s.id} className="p-4 group cursor-pointer hover:shadow-md">
            <div className="h-24 rounded-lg mb-3 flex overflow-hidden">
              {s.colors.map(c => <div key={c} className="flex-1" style={{background:c}}/>)}
            </div>
            <div className="flex items-start justify-between mb-1">
              <h3 className="font-semibold text-sm">{s.name}</h3>
              <Badge variant="outline" className="text-xs">{s.category}</Badge>
            </div>
            <p className="text-xs text-muted-foreground mb-2">{s.desc}</p>
            <div className="flex gap-1 opacity-0 group-hover:opacity-100 transition">
              <Button size="sm" variant="ghost" className="text-xs px-2 py-1">使用</Button>
              <Button size="sm" variant="ghost"><Eye className="w-3 h-3"/></Button>
            </div>
          </Card>
        ))}
      </div>
    </div>
  );
}
