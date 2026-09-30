"use client";

import { Suspense, useState, useEffect } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import Link from "next/link";
import { Sparkles } from "lucide-react";
import { Input } from "@/components/ui/input";
import { Card } from "@/components/ui/card";
import { authApi } from "@/lib/api";
import { setToken, setRefreshToken, setUser, isAuthenticated } from "@/lib/auth";

function LoginForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const isRegister = searchParams.get("mode") === "register";
  const demoMode = process.env.NEXT_PUBLIC_DEMO_MODE === "true";

  const [email, setEmail] = useState("test@example.com");
  const [password, setPassword] = useState("test123456");
  const [name, setName] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if (isAuthenticated()) router.push("/dashboard");
  }, [router]);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError("");
    try {
      if (demoMode) {
        setToken("demo_token_" + Date.now());
        setRefreshToken("demo_refresh_" + Date.now());
        setUser({ id: "demo_user", email, name: name || "演示用户" });
      } else {
        const result = isRegister
          ? await authApi.register(email, password, name || "新用户")
          : await authApi.login(email, password);
        if (!result?.access_token) throw new Error("登录接口未返回 access_token");
        setToken(result.access_token);
        if (result.refresh_token) setRefreshToken(result.refresh_token);
        if (result.user) setUser(result.user);
      }
      router.push("/dashboard");
    } catch (err) {
      setError(err instanceof Error ? err.message : "登录失败");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center p-6 bg-[#f5f5f7]">
      <Card className="w-full max-w-md p-8 rounded-2xl shadow-apple-md border border-border/60 bg-white">
        <div className="text-center mb-8">
          <Link href="/" className="inline-flex items-center gap-2 mb-4">
            <div className="w-12 h-12 rounded-2xl bg-[#007AFF] flex items-center justify-center">
              <Sparkles className="w-7 h-7 text-white" />
            </div>
          </Link>
          <h1 className="text-[28px] font-semibold tracking-tight text-[#1d1d1f]">
            {isRegister ? "创建账号" : "欢迎回来"}
          </h1>
          <p className="text-[15px] text-[#86868b] mt-1.5">
            {isRegister ? "开始你的AI创意之旅" : "继续创作精彩内容"}
          </p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4.5">
          {isRegister && (
            <div>
              <label className="block text-[14px] font-medium mb-1.5 text-[#1d1d1f]">昵称</label>
              <Input
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="你的名字"
                className="h-11 rounded-xl bg-[#f5f5f7] border-transparent focus:bg-white focus:border-[#007AFF]/30 focus:ring-4 focus:ring-[#007AFF]/10"
              />
            </div>
          )}
          <div>
            <label className="block text-[14px] font-medium mb-1.5 text-[#1d1d1f]">邮箱</label>
            <Input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="you@example.com"
              required
              className="h-11 rounded-xl bg-[#f5f5f7] border-transparent focus:bg-white focus:border-[#007AFF]/30 focus:ring-4 focus:ring-[#007AFF]/10"
            />
          </div>
          <div>
            <label className="block text-[14px] font-medium mb-1.5 text-[#1d1d1f]">密码</label>
            <Input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="至少6位"
              required
              minLength={6}
              className="h-11 rounded-xl bg-[#f5f5f7] border-transparent focus:bg-white focus:border-[#007AFF]/30 focus:ring-4 focus:ring-[#007AFF]/10"
            />
          </div>

          {error && (
            <div className="text-sm text-[#ff3b30] bg-[#ff3b30]/10 p-3 rounded-xl">
              {error}
            </div>
          )}

          <button 
            type="submit" 
            disabled={loading}
            className="w-full h-11 rounded-xl bg-[#007AFF] text-white font-medium text-[15px] hover:bg-[#0066cc] active:scale-[0.99] transition-all duration-200 disabled:opacity-50"
          >
            {loading ? "进入中..." : isRegister ? "注册并进入" : demoMode ? "演示登录" : "登录"}
          </button>
        </form>

        <div className="mt-6 text-center text-sm text-[#86868b]">
          {isRegister ? (
            <>
              已有账号？{" "}
              <Link href="/login" className="text-[#007AFF] hover:underline">
                去登录
              </Link>
            </>
          ) : (
            <>
              还没账号？{" "}
              <Link href="/login?mode=register" className="text-[#007AFF] hover:underline">
                免费注册
              </Link>
            </>
          )}
        </div>

        <div className="mt-4 p-3 bg-[#f5f5f7] rounded-xl text-xs text-[#86868b] text-center">
          {process.env.NEXT_PUBLIC_DEMO_MODE === "true" ? "当前为演示模式，不需要后端服务" : "请使用已注册的账号登录"}
        </div>
      </Card>
    </div>
  );
}


export default function LoginPage() {
  return (
    <Suspense fallback={<div className="min-h-screen flex items-center justify-center p-6 bg-[#f5f5f7]">加载中...</div>}>
      <LoginForm />
    </Suspense>
  );
}
