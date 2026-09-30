import Link from "next/link";
import { Sparkles, Wand2, Layers, Zap, ChevronRight } from "lucide-react";
import { Button } from "@/components/ui/button";

export default function HomePage() {
  return (
    <div className="min-h-screen bg-white">
      {/* Header */}
      <header className="border-b border-border/60 sticky top-0 z-50 bg-white/80 backdrop-blur-xl">
        <div className="max-w-6xl mx-auto px-6 h-16 flex items-center justify-between">
          <Link href="/" className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-lg bg-[#007AFF] flex items-center justify-center">
              <Sparkles className="w-5 h-5 text-white" />
            </div>
            <span className="text-xl font-semibold text-[#1d1d1f]">Mago</span>
          </Link>
          <nav className="hidden md:flex items-center gap-6 text-sm text-[#86868b]">
            <Link href="#features" className="hover:text-[#1d1d1f]">功能</Link>
            <Link href="#workflow" className="hover:text-[#1d1d1f]">工作流</Link>
            <Link href="#pricing" className="hover:text-[#1d1d1f]">价格</Link>
          </nav>
          <div className="flex items-center gap-3">
            <Link href="/login">
              <Button variant="ghost">登录</Button>
            </Link>
            <Link href="/login?mode=register">
              <Button>免费开始</Button>
            </Link>
          </div>
        </div>
      </header>

      {/* Hero */}
      <section className="py-20 px-6">
        <div className="max-w-4xl mx-auto text-center">
          <h1 className="text-[56px] leading-[1.05] font-semibold text-[#1d1d1f] tracking-tight mb-6">
            从想法到成片，<br/>10分钟搞定
          </h1>
          <p className="text-[19px] text-[#86868b] max-w-2xl mx-auto mb-8 leading-relaxed">
            Mago AI创意大脑，多Agent协作帮你完成热点洞察→创意发散→脚本创作→分镜设计→12个AIGC模型专业提示词全流程，一键推送到Mago平台生成视频。
          </p>
          <div className="flex items-center justify-center gap-4">
            <Link href="/login?mode=register">
              <Button size="lg" className="text-base px-8">
                免费开始创作 <ChevronRight className="w-4 h-4 ml-1"/>
              </Button>
            </Link>
            <Link href="#workflow">
              <Button variant="secondary" size="lg">了解工作流</Button>
            </Link>
          </div>
        </div>
      </section>

      {/* Features */}
      <section id="features" className="py-16 px-6 bg-[#f5f5f7]">
        <div className="max-w-6xl mx-auto">
          <h2 className="text-[32px] font-semibold text-[#1d1d1f] text-center mb-12">完整创意工作流</h2>
          <div className="grid md:grid-cols-3 gap-6">
            {[
              {icon: Wand2, title: "热点智能洞察", desc: "自动抓取多平台热点数据，AI分析爆款规律，为你推荐高潜力选题方向。"},
              {icon: Layers, title: "多Agent协作", desc: "8个专业Agent协同：创意总监→钩子专家→编剧→分镜师→评审→合规→节奏优化。"},
              {icon: Zap, title: "一键生成提示词", desc: "自动生成12个主流AIGC模型的专业提示词，无需手动调试参数。"},
            ].map((feature, i) => (
              <div key={i} className="card-apple p-6">
                <div className="w-12 h-12 rounded-xl bg-[#007AFF]/10 flex items-center justify-center mb-4">
                  <feature.icon className="w-6 h-6 text-[#007AFF]" />
                </div>
                <h3 className="text-[19px] font-semibold text-[#1d1d1f] mb-2">{feature.title}</h3>
                <p className="text-[15px] text-[#86868b] leading-relaxed">{feature.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Workflow */}
      <section id="workflow" className="py-20 px-6">
        <div className="max-w-4xl mx-auto">
          <h2 className="text-[32px] font-semibold text-[#1d1d1f] text-center mb-4">简单四步，出片更快</h2>
          <p className="text-[17px] text-[#86868b] text-center mb-12">不用再纠结写Prompt、调参数，专注你的创意</p>
          <div className="space-y-4">
            {[
              {step: "01", title: "输入你的想法", desc: "模糊描述你的创意方向，或者让AI推荐当前热点选题"},
              {step: "02", title: "AI自动创作", desc: "多Agent协作生成脚本、分镜、提示词，快速模式3分钟出结果"},
              {step: "03", title: "人工调整优化", desc: "关键节点可以人工修改调整，满意后继续后续流程"},
              {step: "04", title: "一键生成视频", desc: "提示词包直接推送到Mago平台，批量生成12个模型的结果"},
            ].map((item, i) => (
              <div key={i} className="card-apple p-6 flex items-center gap-6">
                <div className="text-[32px] font-semibold text-[#007AFF] w-16 flex-shrink-0">{item.step}</div>
                <div>
                  <h3 className="text-[17px] font-semibold text-[#1d1d1f] mb-1">{item.title}</h3>
                  <p className="text-[15px] text-[#86868b]">{item.desc}</p>
                </div>
              </div>
            ))}
          </div>
          <div className="mt-12 text-center">
            <Link href="/login?mode=register">
              <Button size="lg">立即开始体验</Button>
            </Link>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-border/60 py-8 px-6 text-center text-[12px] text-[#86868b]">
        © 2026 Mago AI 创意平台 · 让AIGC创作更简单
      </footer>
    </div>
  );
}
