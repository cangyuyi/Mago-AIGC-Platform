"use client";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Search, BookOpen, Film, Lightbulb, Wand2 } from "lucide-react";
import { apiFetch } from "@/lib/auth";

const collections = [
  { id: "creative_knowledge", name: "创意理论", icon: Lightbulb, desc: "钩子/叙事/CTA/情绪曲线" },
  { id: "prompt_knowledge", name: "提示词技巧", icon: Wand2, desc: "模型提示词/风格/参数" },
  { id: "cinematography_knowledge", name: "镜头语言", icon: Film, desc: "景别/运镜/光线术语" },
];

export default function KnowledgePage() {
  const [query, setQuery] = useState("");
  const [activeCollection, setActiveCollection] = useState("creative_knowledge");
  const [results, setResults] = useState<any[]>([]);
  const [searched, setSearched] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function search() {
    if (!query.trim()) return;
    setLoading(true);
    setError(null);
    try {
      const data = await apiFetch<{ results?: any[] }>(`/api/agent/knowledge/search?q=${encodeURIComponent(query)}&collection=${encodeURIComponent(activeCollection)}&top_k=10`);
      setResults(data.results || []);
    } catch (e) {
      setResults([]);
      setError(e instanceof Error ? e.message : "知识库搜索失败，请稍后重试");
    } finally {
      setLoading(false);
      setSearched(true);
    }
  }

  return (
    <div className="p-6 max-w-5xl mx-auto">
      <div className="mb-6">
        <h1 className="text-2xl font-bold flex items-center gap-2"><BookOpen className="w-6 h-6"/>知识库</h1>
        <p className="text-sm text-muted-foreground mt-1">创意理论、镜头语言、提示词技巧——可搜索复用</p>
      </div>

      <div className="flex gap-2 mb-4 flex-wrap">
        {collections.map(c=>{
          const Icon = c.icon;
          return(
            <button key={c.id} onClick={()=>setActiveCollection(c.id)}
              className={"px-4 py-2 rounded-lg border text-sm flex items-center gap-2 transition "+
                (activeCollection===c.id?"bg-primary text-primary-foreground border-primary":"border-border hover:bg-muted")}>
              <Icon className="w-4 h-4"/>{c.name}
            </button>
          );
        })}
      </div>

      <div className="flex gap-2 mb-6">
        <div className="flex-1 relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground"/>
          <input value={query} onChange={e=>setQuery(e.target.value)}
            onKeyDown={e=>e.key==="Enter"&&search()}
            placeholder="搜索创意理论、镜头术语、提示词技巧..."
            className="w-full pl-10 pr-4 py-2.5 rounded-lg border border-border bg-background text-sm"/>
        </div>
        <Button onClick={search} disabled={loading}>{loading?"搜索中...":"搜索"}</Button>
      </div>

      {error && <p className="mb-4 text-sm text-destructive">{error}</p>}

      {searched && (
        <div>
          <p className="text-sm text-muted-foreground mb-3">找到 {results.length} 条相关知识</p>
          <div className="space-y-3">
            {results.map((r,i)=>(
              <Card key={i} className="p-4">
                <div className="flex items-start justify-between mb-1">
                  <h3 className="font-semibold text-sm">{r.name||r.title||"知识点"}</h3>
                  <Badge variant="outline">{(r.score*100).toFixed(0)}%匹配</Badge>
                </div>
                {r.category && <Badge variant="outline" className="mb-2 text-xs">{r.category}</Badge>}
                {r.content && <p className="text-sm text-muted-foreground">{r.content}</p>}
                {r.example && <p className="text-xs text-primary mt-1">例：{r.example}</p>}
                {r.term_cn && <p className="text-xs text-muted-foreground mt-1">{r.term_cn} / {r.term_en}</p>}
                {r.prompt_fragment_en && <p className="text-xs font-mono bg-muted/50 p-2 rounded mt-1">{r.prompt_fragment_en}</p>}
                {r.tags && r.tags.length>0 && <div className="flex gap-1 mt-2 flex-wrap">
                  {r.tags.map((t:string,j:number)=><Badge key={j} variant="outline" className="text-xs">{t}</Badge>)}
                </div>}
              </Card>
            ))}
            {results.length===0 && <div className="text-center text-muted-foreground py-8">未找到相关知识，换个关键词试试</div>}
          </div>
        </div>
      )}

      {!searched && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {collections.map(c=>{
            const Icon = c.icon;
            return(
              <Card key={c.id} className="p-6 cursor-pointer hover:shadow-md transition"
                onClick={()=>setActiveCollection(c.id)}>
                <Icon className="w-8 h-8 text-primary mb-3"/>
                <h3 className="font-semibold mb-1">{c.name}</h3>
                <p className="text-sm text-muted-foreground">{c.desc}</p>
              </Card>
            );
          })}
        </div>
      )}
    </div>
  );
}
