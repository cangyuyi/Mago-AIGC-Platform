"use client";

import { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Plus, User, Eye, Trash2, Loader2 } from "lucide-react";
import { charactersApi, type Character } from "@/lib/api";

const emptyForm = { name: "", description: "", gender: "female", age_appearance: "young_adult", personality_vibe: "", prompt_fragment: "" };

export default function CharactersPage() {
  const [characters, setCharacters] = useState<Character[]>([]);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState(emptyForm);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [deleting, setDeleting] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await charactersApi.list();
      setCharacters(result.items ?? []);
    } catch (err) {
      setError(err instanceof Error ? err.message : "角色加载失败");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { void load(); }, []);

  const submit = async () => {
    if (!form.name.trim()) return setError("请填写角色名称");
    setSaving(true);
    setError(null);
    try {
      await charactersApi.create({
        ...form,
        name: form.name.trim(),
        prompt_fragment: form.prompt_fragment.trim() || form.description.trim(),
      });
      setForm(emptyForm);
      setShowForm(false);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "角色创建失败");
    } finally {
      setSaving(false);
    }
  };

  const remove = async (id: string) => {
    if (!window.confirm("确定删除这个角色吗？")) return;
    setDeleting(id);
    setError(null);
    try {
      await charactersApi.delete(id);
      setCharacters((items) => items.filter((item) => item.id !== id));
    } catch (err) {
      setError(err instanceof Error ? err.message : "角色删除失败");
    } finally {
      setDeleting(null);
    }
  };

  return (
    <div className="p-6 max-w-6xl mx-auto">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold flex items-center gap-2"><User className="w-6 h-6" />角色管理</h1>
          <p className="text-sm text-muted-foreground mt-1">创建可跨镜头复用的角色形象，确保 AI 生成时人物一致性</p>
        </div>
        <Button onClick={() => setShowForm((value) => !value)} className="gap-2"><Plus className="w-4 h-4" />新建角色</Button>
      </div>

      {error && <p className="mb-4 text-sm text-destructive" role="alert">{error}</p>}

      {showForm && (
        <Card className="p-6 mb-6">
          <h3 className="font-semibold mb-4">创建新角色</h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
            <label className="text-sm font-medium">角色名称
              <input className="w-full mt-1 px-3 py-2 rounded-lg border border-border bg-background text-sm" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} placeholder="如：小美" />
            </label>
            <label className="text-sm font-medium">性别
              <select className="w-full mt-1 px-3 py-2 rounded-lg border border-border bg-background text-sm" value={form.gender} onChange={(e) => setForm({ ...form, gender: e.target.value })}>
                <option value="female">女</option><option value="male">男</option><option value="non-binary">非二元</option>
              </select>
            </label>
            <label className="md:col-span-2 text-sm font-medium">角色描述
              <textarea className="w-full mt-1 px-3 py-2 rounded-lg border border-border bg-background text-sm min-h-[90px]" value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} placeholder="描述角色的外貌、服装、气质等" />
            </label>
            <label className="md:col-span-2 text-sm font-medium">Prompt 片段（可选）
              <textarea className="w-full mt-1 px-3 py-2 rounded-lg border border-border bg-background text-sm min-h-[70px]" value={form.prompt_fragment} onChange={(e) => setForm({ ...form, prompt_fragment: e.target.value })} placeholder="留空时使用角色描述" />
            </label>
          </div>
          <div className="flex gap-2">
            <Button onClick={() => void submit()} disabled={saving}>{saving && <Loader2 className="w-4 h-4 mr-2 animate-spin" />}创建角色</Button>
            <Button variant="ghost" onClick={() => setShowForm(false)}>取消</Button>
          </div>
        </Card>
      )}

      {loading ? <div className="py-12 text-center text-muted-foreground">加载中...</div> : characters.length === 0 ? (
        <Card className="py-12 text-center text-muted-foreground">还没有角色，点击“新建角色”开始创建。</Card>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {characters.map((character) => (
            <Card key={character.id} className="p-4 group">
              <div className="aspect-square rounded-lg bg-[#f5f5f7] mb-3 flex items-center justify-center"><User className="w-16 h-16 text-muted-foreground" /></div>
              <div className="flex items-start justify-between mb-1">
                <h3 className="font-semibold">{character.name}</h3>
                <div className="flex gap-1 opacity-0 group-hover:opacity-100 transition">
                  <Button size="sm" variant="ghost" title="查看"><Eye className="w-3 h-3" /></Button>
                  {!character.is_preset && <Button size="sm" variant="ghost" title="删除" onClick={() => void remove(character.id)} disabled={deleting === character.id}><Trash2 className="w-3 h-3" /></Button>}
                </div>
              </div>
              <div className="flex gap-1 mb-2"><Badge variant="outline">{character.gender === "female" ? "女" : character.gender === "male" ? "男" : character.gender || "未设置"}</Badge>{character.personality_vibe && <Badge variant="outline">{character.personality_vibe}</Badge>}</div>
              <p className="text-xs text-muted-foreground line-clamp-2">{character.prompt_fragment || character.description || "暂无描述"}</p>
              {character.faceid_weight != null && <div className="mt-2 text-xs text-muted-foreground">FaceID 权重: {character.faceid_weight}</div>}
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
