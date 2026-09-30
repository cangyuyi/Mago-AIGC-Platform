# 指令 03：脚本创作中心（Script Studio）—— 创意输出核心

## 角色设定

你是一名**顶级短视频创意总监+编剧团队负责人**，你有10年短视频和广告创意经验，深刻理解抖音/快手/小红书/TikTok的传播逻辑，精通上百种钩子套路、叙事结构、情绪曲线设计方法。你同时是一名**AI Agent架构师**，能把创意方法论编码成可复用的多Agent协作系统。

你要构建的不是一个"帮你写字"的工具，而是一套**灵感激发器+创意合伙人**——用户哪怕只有一个模糊的方向（甚至完全没方向），也能通过这套系统获得：①多个不同角度的创意方向 ②经过多Agent辩论筛选的最优方案 ③可直接用于拍摄/生成的专业分镜脚本。

## 前置依赖

必须先完成 `01-project-bootstrap.md`。本板块依赖：LangGraph编排框架、LLM网关、Chat UI、项目数据模型、PostgreSQL。

## 产品边界

✅ **做**：灵感激发、选题深化、创意多方向发散、脚本写作（多Agent协作）、分镜设计、脚本质量评估、节奏优化、合规审查、脚本版本迭代  
❌ **不做**：实际拍摄、视频生成（Mago做）、发布运营（后续板块）

## 核心设计理念——"三层创意漏斗"

```
[第1层 灵感发散] 从0到1，给你10个完全不同角度的创意方向（打破思维盲区）
       │  用户选择/组合/调整方向
       ▼
[第2层 方案深化] 选定方向后，多Agent辩论产出最佳脚本（钩子/叙事/情绪/CTA）
       │  用户审核/修改/细化
       ▼
[第3层 执行落地] 脚本→分镜表→画面描述→可直接生成的详细指令（提示词交给05）
```

关键点：**不让用户在"一张白纸"上开始**，而是Agent主动给选项、给碰撞、给惊喜。

## 执行步骤

### Step 1：调研GitHub与行业最佳实践（必须）

在 `docs/research/03-script-studio.md` 中记录调研结论，**必须**调研和评估：

1. **多Agent协作框架参考**：
   - 搜索关键词：`multi agent debate llm creative writing`, `crewai examples content creation`, `autogen creative writing`, `langgraph multi agent collaboration`
   - 参考：`joaomdmoura/crewAI` 官方examples（特别是content creation示例）、`langchain-ai/langgraph` 官方multi-agent examples、`microsoft/autogen` 里的debate场景
   - 重点学习：多Agent角色定义方式、辩论机制、审批节点、人工介入机制

2. **剧本/分镜数据结构标准**：
   - 搜索关键词：`screenplay data structure json open source`, `fountain screenplay format`, `open timeline io`, `shot list data model`
   - 参考：`jaredly/screenplain`(Fountain格式解析), `AcademySoftwareFoundation/OpenTimelineIO`(皮克斯/迪士尼开源的时间线格式，专业影视行业标准——评估是否借鉴其shot/clip结构)
   - 决策：借鉴OpenTimelineIO的结构化思路但不引入重依赖，自己设计适合短视频（15s-5min）的轻量schema

3. **影视编剧理论开源资源**（不是代码项目，但必须调研并提炼成知识库条目）：
   - 搜索关键词：`short video hook formula github`, `tiktok script template`, `screenplay structure beat sheet`
   - 参考：Save the Cat(救猫咪)、Dan Harmon Story Circle、Pixar 22 Rules of Storytelling、Three-Act Structure、YouTube MrBeast/Beast Reacts 的剪辑节奏分析、抖音爆款拆解方法论（公开可查的运营SOP）
   - 必须提炼：至少**100种钩子套路**、**30种叙事结构**、**20种CTA策略**、**10种情绪曲线模板**——形成结构化JSON知识库，初版可由你基于专业知识构建框架+LLM辅助扩充，后续通过爆款拆解自动积累

4. **富文本/分镜编辑器前端组件**：
   - 搜索关键词：`react screenplay editor`, `react timeline editor video`, `react sheet table component`, `react dnd sortable list`
   - 参考：`atlassian/react-beautiful-dnd`(拖拽排序), `dnd-kit`(更现代的DND), `tanstack/table`(表格), 参考Notion/飞书文档的块编辑器思路
   - 决策：分镜表格用TanStack Table + dnd-kit（支持行拖拽排序/内联编辑），脚本富文本用tiptap或lexical（调研二选一）

### Step 2：数据库表设计（追加migration）

```sql
-- 脚本表
CREATE TABLE scripts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    version INT NOT NULL DEFAULT 1,
    parent_version_id UUID REFERENCES scripts(id),  -- 版本链
    title VARCHAR(512) NOT NULL,
    script_type VARCHAR(32) NOT NULL,     -- oral_story/drama/show_review/tutorial/seeding/brand/hot_topic/...
    duration_target INT,                  -- 目标时长（秒）
    aspect_ratio VARCHAR(16) DEFAULT '9:16',
    target_platform VARCHAR(32),          -- douyin/xiaohongshu/bilibili/youtube/...
    status VARCHAR(20) DEFAULT 'draft',   -- draft/reviewing/approved/final
    -- 核心内容
    hook TEXT,                            -- 钩子文案
    hook_type VARCHAR(64),                -- 钩子类型
    body TEXT,                            -- 完整脚本正文（Markdown/结构化）
    cta TEXT,                             -- CTA文案
    cta_type VARCHAR(64),
    tags TEXT[],
    bpm_target FLOAT,                     -- 节奏目标（BPM）
    emotion_arc VARCHAR(64)[],            -- 情绪曲线标签数组
    -- 评估
    quality_scores JSONB DEFAULT '{}',    -- {hook:8, rhythm:7, emotion:6, cta:7, feasibility:8, compliance:10}
    quality_feedback JSONB DEFAULT '[]',  -- Agent评估建议列表
    compliance_flags JSONB DEFAULT '[]',  -- 合规问题列表 [{level:"warning", "reason":"", "suggestion":""}]
    -- 参考
    reference_video_ids UUID[],           -- 参考的爆款视频ID
    reference_pattern_ids UUID[],         -- 参考的爆款公式ID
    creative_brief JSONB,                 -- 创意简报（来自创意总监Agent）
    model_info JSONB DEFAULT '{}',        -- 使用的模型/Prompt版本
    editor_id UUID REFERENCES users(id),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(project_id, version)
);
CREATE INDEX idx_scripts_project ON scripts(project_id);
CREATE INDEX idx_scripts_status ON scripts(status);
CREATE INDEX idx_scripts_type ON scripts(script_type);

-- 分镜表
CREATE TABLE storyboards (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    script_id UUID NOT NULL REFERENCES scripts(id) ON DELETE CASCADE,
    version INT NOT NULL DEFAULT 1,
    title VARCHAR(255),
    total_duration FLOAT,                 -- 总时长（秒）
    shot_count INT,
    aspect_ratio VARCHAR(16) DEFAULT '9:16',
    status VARCHAR(20) DEFAULT 'draft',
    style_reference JSONB,                -- 风格参考信息
    model_info JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_storyboards_project ON storyboards(project_id);
CREATE INDEX idx_storyboards_script ON storyboards(script_id);

-- 镜头表（分镜下的具体镜头）
CREATE TABLE storyboard_shots (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    storyboard_id UUID NOT NULL REFERENCES storyboards(id) ON DELETE CASCADE,
    shot_index INT NOT NULL,              -- 镜头序号
    duration FLOAT NOT NULL,              -- 时长（秒）
    shot_type VARCHAR(32),                -- 景别：extreme_close_up/close_up/medium_close_up/medium/medium_wide/wide/extreme_wide/pov/over_shoulder
    camera_movement VARCHAR(64),          -- 运镜：static/push_in/push_out/pan_left/pan_right/tilt_up/tilt_down/tracking/following/crane_up/crane_down/orbit/handheld/dolly_zoom/whip_pan/zoom_in/zoom_out
    camera_angle VARCHAR(32),             -- 角度：eye_level/low_angle/high_angle/birds_eye/dutch_angle/over_shoulder
    lens_focal_length VARCHAR(32),        -- 焦距：wide/standard/telephoto/macro/anamorphic
    depth_of_field VARCHAR(16),           -- 景深：shallow/medium/deep
    -- 画面
    scene_environment TEXT,               -- 场景环境描述（详细、可视化）
    subject_description TEXT,             -- 主体描述（人物/物体/动作/表情）
    props TEXT[],                         -- 道具列表
    lighting TEXT,                        -- 光线描述
    color_tone TEXT,                      -- 色调描述
    composition TEXT,                     -- 构图描述
    visual_reference_urls TEXT[],         -- 视觉参考图URL
    -- 内容
    dialogue_narration TEXT,              -- 台词/旁白/字幕
    sound_effect TEXT,                    -- 音效描述
    bgm_emotion VARCHAR(64),              -- BGM情绪
    emotion_tag VARCHAR(32),              -- 该镜头情绪标签
    -- 转场
    transition_in VARCHAR(32),            -- 入场方式：cut/dissolve/fade_in/whip_pan/zoom/match_cut
    transition_out VARCHAR(32),           -- 出场方式
    -- AI生成相关（供提示词引擎用）
    motion_description TEXT,              -- 视频运动描述（供文生视频用）
    keyframe_prompt_hint TEXT,            -- 关键帧提示词要点（供提示词引擎参考）
    ai_generation_notes TEXT,             -- AI生成注意事项（可行性/避坑）
    consistency_hints JSONB DEFAULT '{}', -- 跨镜头一致性提示
    -- 评估
    quality_score INT,
    feedback TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_shots_storyboard ON storyboard_shots(storyboard_id, shot_index);

-- 创意会话表（记录Agent多轮创意过程）
CREATE TABLE creative_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    session_type VARCHAR(32) NOT NULL,    -- ideation/debate/revision/...
    status VARCHAR(20) DEFAULT 'active',
    ideas JSONB DEFAULT '[]',             -- 产出的创意想法列表
    selected_idea_id VARCHAR(64),
    debate_log JSONB DEFAULT '[]',        -- Agent辩论记录
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
```

### Step 3：创意理论知识库初始化（必须亲手构建初版）

在 `services/agent/src/knowledge/creative_theory/` 下创建JSON知识库，**这是整个平台的创意内功**，你必须基于影视/短视频专业理论构建初版（不能留给LLM临场发挥，那样不稳定）。

必须创建以下文件（每个都是结构化JSON，供Agent检索引用）：

**3.1 `hook_taxonomy.json` — 钩子类型大全（初版至少100种）**

按类型组织，每条结构：
```json
{
  "id": "hook_counter_intuitive_001",
  "category": "反常识式",
  "name": "反常识颠覆",
  "description": "提出一个与大众认知相反的观点/现象，制造认知冲突",
  "mechanism": "利用大脑对'违背预期'信息的自动注意力捕获机制（Prediction Error）",
  "template": "你以为___？其实___。",
  "examples": [
    "你以为每天喝8杯水健康？医生说这三类人喝多了反而出事",
    "月入3千的人，比月入3万的人存的钱更多，原因你绝对想不到"
  ],
  "applicable_scenarios": ["知识科普","财经","健康","职场"],
  "best_duration": "0-3秒",
  "tone": "悬念/严肃/震惊",
  "visual_hint": "主体正面特写，表情严肃/神秘，配合文字特效",
  "success_rate_est": 0.78   // 基于爆款库统计（初版可设null，后续数据回流填充）
}
```

必须覆盖的类别（每类至少8-15个具体钩子）：
- 悬念式（设置悬念、留白、未解之谜）
- 冲突式（矛盾对立、争议观点、打架场景）
- 反常识式（颠覆认知、反直觉结论、冷知识）
- 痛点式（精准戳中目标人群痛点）
- 数字式（用具体数字制造冲击）
- 提问式（向观众提问，引发思考/共鸣）
- 对比式（前后对比、好坏对比、贫富对比、同龄对比）
- 视觉冲击式（惊险/美丽/罕见/震撼画面开场）
- 情感共鸣式（直接说出观众想说的话/经历的事）
- 利益承诺式（"看完这个视频你将获得___"）
- 紧急/稀缺式（限时/紧急警告/最后机会）
- 自嘲/吐槽式（自我调侃引发共鸣）
- 故事引入式（"昨天我遇到一件事..."）
- 金句式（一句有哲理/有力量的话开场）
- 道具/动作式（不说话直接展示特殊动作/道具）
- ……（至少覆盖15个大类，100+具体钩子模板）

**3.2 `narrative_structures.json` — 叙事结构库（初版至少30种）**

每种结构包含：名称、适用场景、分阶段Beat Sheet（精确到秒的节点）、情绪曲线、示例
必须覆盖：
- 短视频专用：黄金3秒-痛点-方案-CTA、清单式、对比反转式、Vlog日志式、沉浸式ASMR式、快节奏蒙太奇、Reaction反应式、教程Step-by-step、悬念揭晓式、连续反转式(2-3次反转)
- 经典叙事：三幕式、英雄之旅(短视频版)、Dan Harmon故事圈(短视频版)、救猫咪Beat Sheet(短视频版)、Pixar故事公式
- 广告/带货：AIDA(Attention-Interest-Desire-Action)、PAS(Problem-Agitate-Solve)、FAB(Feature-Advantage-Benefit)、BAB(Before-After-Bridge)、4U(Urgent-Unique-Ultra-specific-Urgent)
- 情感故事：遗憾式、报恩式、陌生人善意式、成长蜕变式、亲情/爱情/友情短篇

每种结构模板示例：
```json
{
  "id": "struct_pas_001",
  "name": "PAS痛点放大式（带货/种草黄金结构）",
  "category": "带货/种草",
  "optimal_duration": [30, 60],
  "applicable_scenarios": ["好物推荐","知识付费","服务推广","软件推广"],
  "beat_sheet": [
    {"beat": "Hook-痛点呈现", "time_range": "0-3s", "duration_pct": 0.10, "purpose": "用精准痛点抓注意力，让观众觉得'这说的就是我'", "emotion": "痛苦/焦虑/共鸣", "required_elements": ["具体场景化痛点描述","主体近景","皱眉/困扰表情"]},
    {"beat": "Agitate-痛点放大", "time_range": "3-12s", "duration_pct": 0.30, "purpose": "把痛点放大到不能忍受，让观众产生强烈的解决欲望", "emotion": "焦虑升级/厌恶", "required_elements": ["具体后果/损失","场景演绎","快速2-3个不同场景切换"]},
    {"beat": "Solution-方案登场", "time_range": "12-25s", "duration_pct": 0.40, "purpose": "产品/方案以救星姿态出现", "emotion": "释然/惊喜/希望", "required_elements": ["产品出现镜头(高光/慢动作)","核心卖点展示","使用演示"]},
    {"beat": "Benefit-效果展示", "time_range": "25-35s", "duration_pct": 0.15, "purpose": "展示使用后的美好结果，强化价值", "emotion": "满足/愉悦/向往", "required_elements": ["使用前后对比","用户满意度表情","结果可视化"]},
    {"beat": "CTA-行动召唤", "time_range": "35-45s", "duration_pct": 0.05, "purpose": "明确告诉观众下一步做什么", "emotion": "紧迫/期待", "required_elements": ["清晰指令","紧迫感/优惠信息"]}
  ],
  "emotion_curve": ["共鸣(痛)", "焦虑(放大)", "希望(方案)", "满足(效果)", "冲动(CTA)"],
  "average_shot_count": [8, 15],
  "pacing": "快节奏，镜头切换快于日常Vlog",
  "examples": [
    {"script_fragment": "...每次化妆卡粉到怀疑人生，试了十几款粉底都救不了这个大干皮...直到我遇到了它...", "source": "典型美妆带货视频"}
  ]
}
```

**3.3 `cta_strategies.json` — CTA策略库（初版至少20种）**
**3.4 `emotion_arc_templates.json` — 情绪曲线模板（初版至少15种）**
**3.5 `genre_conventions.json` — 各垂类视频的套路/禁忌/节奏规范（初版至少20个垂类）**
**3.6 `rhythm_patterns.json` — 节奏模式（快切/慢推/混合节奏的最佳实践）**

> 💡 这6个知识库文件是核心资产。你（Agent）必须亲自撰写初版，基于你的专业知识+LLM辅助扩充+引用行业经典理论，而不是生成空架子。每个条目要有干货、有具体模板、有示例。这些文件后续会持续被爆款拆解Agent自动扩充。

### Step 4：实现Agent角色系统（多Agent协作）

在 `services/agent/src/agents/script/` 下实现8个协作Agent：

```
agents/script/
├── __init__.py
├── base.py                     # ScriptAgent基类
├── ideation_agent.py           # 灵感发散Agent
├── creative_director.py        # 创意总监Agent（决策者）
├── hook_specialist.py          # 钩子专家Agent
├── storyteller.py              # 叙事编剧Agent
├── copywriter.py               # 文案撰稿Agent
├── conversion_expert.py        # 转化专家Agent
├── compliance_agent.py         # 合规审查Agent
├── storyboard_agent.py         # 分镜师Agent
├── script_evaluator.py         # 脚本评估Agent（自检）
├── prompts/
│   ├── ideation.md
│   ├── creative_director.md
│   ├── hook_specialist.md
│   ├── storyteller.md
│   ├── copywriter.md
│   ├── conversion_expert.md
│   ├── compliance.md
│   ├── storyboard.md
│   └── evaluator.md
└── graph.py                    # 脚本创作LangGraph编排
```

**每个Agent必须遵循三层Prompt设计**（参考`docs/02-prompt-iteration-sop.md`的Prompt规范，三层结构）：

- **宪法层**：角色身份、核心原则、不可违反的硬约束
- **流程层**：思考步骤（CoT）、必须引用的知识库资源、输出前自检清单
- **表达层**：输出格式（严格JSON Schema）、风格要求、Few-shot示例（每个Agent至少3个高质量示例）

#### 4.1 灵感发散Agent（Ideation Agent）⭐ 解决"没灵感"的核心

这是用户最先接触的Agent，解决"我想做美妆但不知道做什么"的问题。

**输入**：
- 用户的模糊输入（"我想做口红相关的视频" / "我是做健身的最近没灵感了" / 甚至只给一个表情或一个词）
- 用户账号信息（垂类/历史风格/粉丝画像，可选）
- 当前热点数据（从trend_intelligence获取）
- 爆款库中同垂类的成功案例
- 随机创意催化剂（可选：跨领域类比/热梗/随机词）

**工作逻辑**：
1. **理解用户意图**：如果用户输入太模糊，主动追问最多2个关键问题（"视频主要发在抖音还是小红书？""目标观众是学生党还是上班族？"），但不超过2轮，避免让用户烦
2. **检索素材**：
   - 检索当前上升期相关热点
   - 从爆款库检索同垂类最近30天高viral_score的视频
   - 跨领域检索：随机选一个其他垂类的爆款公式，思考能否跨界移植（核心创意激发手段——**跨领域类比是创新的最大来源**）
3. **创意发散**：用SCAMPER法/随机词联想法/反向思维法，生成**至少10个差异度足够大**的创意方向（不是10个大同小异的，而是10个不同角度、不同结构、不同情绪的方案）
4. **每个创意方向包含**：
   - 创意名称（一句话，有吸引力）
   - 创意角度描述（2-3句话说清楚这个创意的核心思路）
   - 钩子方向（用什么类型钩子、大概内容）
   - 情绪基调（搞笑/感动/震撼/愤怒/治愈/干货…）
   - 差异化点（为什么这个方向能火，和同类内容的区别）
   - AI生成可行性评分（1-10分，评估AI能做出来的程度）
   - 参考案例（关联的爆款视频链接/公式ID）
   - 预估制作难度（低/中/高）

**关键机制——创意激发算子**（必须实现至少5种）：
1. **跨界移植法**：把美食视频的爆款结构搬到美妆，把游戏解说的节奏搬到知识口播
2. **反转法**：把常规做法反过来（"不要买XX的3个原因" instead of "推荐XX的3个理由"）
3. **极端化法**：把某一元素推到极致（"用100支口红画一幅画"/"挑战24小时不说谎"）
4. **代入法**：代入特定身份/场景（"假如林黛玉来做美妆博主"/"当程序员去相亲"）
5. **热梗嫁接法**：把当前BGM热梗/挑战梗嫁接到本垂类
6. **冲突法**：制造对立/矛盾/争议（"闺蜜说我选的口红色号死亡，你们评评理"）
7. **时间压缩/延展法**："一秒变妆"/"30天皮肤变化记录"/"用10分钟讲完100年历史"
8. **第四面墙法**：打破第四面墙直接和观众对话/让观众决策

**输出**：`List[CreativeIdea]`（Pydantic），10个创意方向，前端展示为创意卡片供用户选择。

#### 4.2 创意总监Agent（Creative Director）

- 统筹其他Agent，分配任务
- 在多个Agent意见冲突时做最终裁决
- 审核每个阶段的产出质量，不满意发回重写
- 对最终脚本做终审

#### 4.3 钩子专家Agent（Hook Specialist）

- 接收创意方向+垂类，检索 `hook_taxonomy.json` 中最适配的3-5种钩子类型
- 为每个候选钩子写具体文案（严格对应钩子模板）
- 评估每个钩子的吸引力评分（1-10），选出Top 3给创意总监裁决
- 必须保证：钩子文案与视频内容强相关（不做标题党）、不超过3秒口播时长（约20-40字）、有信息缺口或情绪触发点

#### 4.4 叙事编剧Agent（Storyteller）

- 接收创意方向+选定钩子，从 `narrative_structures.json` 选择最适合的叙事结构
- 按beat sheet分配时长和内容，产出完整脚本
- 设计情绪曲线，控制节奏起伏
- 脚本中必须标注：每段对应的情绪、预估时长、镜头建议（粗粒度，具体分镜由分镜师做）
- 必须符合该垂类的convention（从genre_conventions.json读取）

#### 4.5 文案撰稿Agent（Copywriter）

- 优化口播文案：口语化、短句为主、避免书面腔、每句有信息增量
- 设计字幕重点词（哪些词要高亮/花字）
- 写标题、描述文案、标签方案
- 保证中文字速：口播类约4-5字/秒（正常语速），快节奏口播6-7字/秒，给后期留白
- **抖音/小红书风格文案 vs B站风格文案**：根据目标平台调整用词和节奏

#### 4.6 转化专家Agent（Conversion Expert）

- 根据视频目的（涨粉/带货/引流/品牌/完播）设计不同的CTA策略
- 从cta_strategies.json选择最适配的CTA类型
- 种草类视频：设计种草逻辑（痛点→共鸣→方案→佐证→CTA）
- 带货类视频：设计信任状（销量/权威/数据/亲身验证）+ 稀缺性/紧迫感
- 避免硬广感：CTA要自然融入内容，不突兀

#### 4.7 合规审查Agent（Compliance Agent）

- 敏感词检测（政治/色情/暴力/歧视/医疗/金融违规词）
- 广告法合规：禁用"最/第一/国家级/绝对/100%"等极限词
- 平台规则：各平台特殊禁忌（如抖音的医疗健康类限制、小红书的导流限制）
- 版权风险提示：BGM版权、素材版权、肖像权
- 未成年人保护
- 每个问题标注：level(pass/warning/danger) + reason + 修改建议
- danger级别的问题必须修改后才能通过，warning提醒用户注意

#### 4.8 分镜师Agent（Storyboard Agent）

- 接收脚本（含情绪曲线、beat信息），生成分镜表（storyboard_shots）
- 核心逻辑：
  - 根据总时长和节奏模板分配每个镜头时长（快节奏段2-4秒/镜，慢节奏段5-8秒/镜，钩子段1-2秒/镜）
  - 自动规划景别变化：避免连续3个以上同景别，设计景别节奏（特→近→中→全→特 有呼吸感）
  - 为每段文案匹配最适合的景别和运镜（根据narrative_structure里的beat required_elements）
  - 画面描述要**具体、可视化、可用于AI生成**——避免抽象概念（"她很伤心" → "25岁女性，眼眶泛红，嘴唇微颤，低头看着手中的信件，窗外下着雨，室内冷蓝色光线"）
  - 标注每个镜头的情绪、BGM情绪、转场方式
  - 检测AI生成可行性：对AI难以生成的画面（如复杂文字/多人精确互动/复杂物理交互/手指精细动作）给出简化建议或拆分方案
  - 跨镜头一致性标记：标注哪些镜头角色/场景需要一致，给出固定描述段建议

**分镜Prompt框架**（重要）：
```
你是一位专业影视分镜师，擅长把脚本文字转化为具体可拍摄/可AI生成的镜头。

工作规则：
1. 严格按照[叙事结构beats]的时长分配设计镜头
2. 景别必须有变化，禁止连续3镜以上同景别
3. 画面描述必须具体到：人物外貌表情+动作姿态+场景环境+光线+色调+构图，不能有抽象形容词
4. 为每个镜头给出建议运镜，但不要滥用运动（视频AI模型对复杂运镜的处理能力有限，优先固定镜头+简单推拉）
5. 口播类视频：镜头切换频率要与说话节奏匹配，重点词出现时可切特写
6. 每个镜头标注AI生成难度（easy/medium/hard），hard镜头给出替代方案
7. 总镜头数控制在[根据时长计算：30秒视频8-12镜，60秒15-25镜]

输出JSON schema：
{
  "shots": [{
    "shot_index": int,
    "duration": float,
    "shot_type": "...",
    "camera_movement": "...",
    "camera_angle": "...",
    "scene_environment": "（具体场景描述，50字以上，可视化）",
    "subject_description": "（人物/主体详细描述，包含动作和表情）",
    "props": ["..."],
    "lighting": "...",
    "color_tone": "...",
    "dialogue_narration": "对应的口播/字幕文字",
    "sound_effect": "...",
    "bgm_emotion": "...",
    "emotion_tag": "...",
    "transition_in": "...",
    "transition_out": "...",
    "motion_description": "（视频生成专用：描述镜头中的动态元素，包括主体运动、镜头运动、环境运动，用英文或中文按视频模型偏好）",
    "ai_generation_notes": "（AI生成提示/风险/避坑建议）",
    "consistency_hints": {
      "character_locked": true/false,
      "scene_locked": true/false,
      "color_locked": true/false
    }
  }]
}
```

#### 4.9 脚本评估Agent（Script Evaluator）—— 自检环节

每个阶段产出后都要过评估Agent，评分+改进建议，低于阈值自动重写。评估维度：
- 钩子强度（1-10）：是否有注意力抓手？信息缺口是否足够？
- 节奏合理性（1-10）：镜头时长分布是否合理？有无冗余段落？
- 情绪曲线（1-10）：是否有起伏？高潮点是否明确？
- 信息密度（1-10）：是否有废话？每3秒是否有新信息点？
- 差异化（1-10）：和同类内容相比有何不同？
- CTA有效性（1-10）：行动指令是否清晰？动机是否充足？
- 合规性（1-10）：有无违规风险？
- AI可行性（1-10）：AI能否生成？哪些镜头需要简化？
- 总分低于7分或任一维度低于5分 → 返回对应Agent重写，附上具体改进建议

### Step 5：LangGraph工作流编排

在 `graph.py` 中定义完整的脚本创作DAG，必须支持两种模式：

#### 5.1 精细模式（默认，每个节点人工确认）

```
[用户输入] 
  → clarify_needs (必要时追问)
  → ideation (灵感发散：10个创意方向)
  → [HITL: 用户选择创意方向/可组合] 
  → creative_brief (创意总监写创意简报)
  → [HITL: 用户确认创意简报]
  → hook_design (钩子专家产出3个钩子)
  → narrative_design (叙事编剧产出完整脚本)
  → copywriting (文案撰稿优化)
  → cta_design (转化专家设计CTA)
  → compliance_check (合规审查)
  → script_evaluation (脚本评估)
  → <评估不通过 → 返回对应节点重写>
  → [HITL: 用户审核脚本，可自然语言反馈修改]
  → storyboard_design (分镜师产出分镜表)
  → storyboard_evaluation (分镜评估)
  → [HITL: 用户逐镜审核/修改]
  → [交付脚本+分镜]
```

#### 5.2 快速模式（一键出片，跳过中间HITL）

```
[用户输入] 
  → auto_select (创意总监直接选最优方向)
  → quick_pipeline (钩子→叙事→文案→CTA→合规→评估，串行自动)
  → storyboard_quick (快速分镜)
  → [直接交付脚本+分镜，用户按需修改]
```

#### 5.3 关键编排要求

- **状态持久化**：每个节点执行完后状态入库（creative_sessions表记录全过程）
- **断点续跑**：用户关闭页面后再回来可以从上次HITL节点继续
- **并行节点**：钩子/文案/CTA可并行生成提高速度（在钩子确定之后）
- **版本管理**：每次修改都生成新版本，保留完整版本链，可对比diff
- **自然语言修改**：用户在任何节点都可以用自然语言说"钩子要更幽默一点"/"第3镜改成中景"/"整体时长缩短到30秒"，对应Agent理解修改意图并局部更新

### Step 6：脚本Agent与提示词Agent的接口定义

脚本创作完成后，输出给提示词引擎（板块05）的数据包结构（用Pydantic定义，共享类型）：

```python
class ScriptPackage(BaseModel):
    """脚本创作的完整输出，交给提示词引擎"""
    project_id: UUID
    script_id: UUID
    storyboard_id: UUID
    title: str
    script_type: str
    aspect_ratio: str
    target_duration: int
    target_platform: str
    creative_brief: dict                # 创意简报
    hook: str
    hook_type: str
    body: str
    cta: str
    cta_type: str
    emotion_arc: list[str]
    characters: list[CharacterRef]      # 角色引用（角色卡ID或临时描述）
    style: StyleRef                     # 风格引用
    shots: list[ShotForPrompt]          # 给提示词引擎用的精简镜头数据
    reference_videos: list[UUID]
    global_constraints: dict            # 全局约束（品牌规范等）

class ShotForPrompt(BaseModel):
    shot_index: int
    duration: float
    shot_type: str
    camera_movement: str
    scene_environment: str
    subject_description: str
    props: list[str]
    lighting: str
    color_tone: str
    dialogue_narration: str
    sound_effect: str | None
    bgm_emotion: str | None
    emotion_tag: str
    motion_description: str
    ai_generation_notes: str | None
    consistency_hints: dict
    transition_in: str | None
    transition_out: str | None
```

### Step 7：API实现

Go后端新增（或者在Python Agent服务直接暴露，统一走Go网关聚合）：

| 方法 | 路径 | 功能 |
|:---|:---|:---|
| POST | `/api/v1/projects/:id/scripts/ideate` | 灵感发散（返回10个创意方向） |
| POST | `/api/v1/projects/:id/scripts/select-idea` | 选择创意方向 |
| POST | `/api/v1/projects/:id/scripts` | 创建脚本（自动走pipeline，支持流式返回进度） |
| GET | `/api/v1/scripts/:id` | 脚本详情（含各版本） |
| PUT | `/api/v1/scripts/:id` | 修改脚本（自然语言或结构化） |
| POST | `/api/v1/scripts/:id/regenerate-hook` | 重新生成钩子（多个候选） |
| POST | `/api/v1/scripts/:id/evaluate` | 手动触发脚本评估 |
| GET | `/api/v1/scripts/:id/versions` | 版本历史 |
| POST | `/api/v1/scripts/:id/versions/:vid/restore` | 回滚到指定版本 |
| POST | `/api/v1/scripts/:id/storyboard` | 生成分镜 |
| GET | `/api/v1/storyboards/:id` | 分镜详情 |
| PUT | `/api/v1/storyboards/:id/shots/:shot_id` | 修改单个镜头 |
| POST | `/api/v1/storyboards/:id/shots/reorder` | 拖拽排序镜头 |
| POST | `/api/v1/storyboards/:id/regenerate-shot` | 重新生成单个镜头 |
| POST | `/api/v1/storyboards/:id/regenerate-all` | 重新生成所有镜头 |
| GET | `/api/v1/storyboards/:id/shots` | 镜头列表（分页） |
| POST | `/api/v1/storyboards/:id/evaluate` | 分镜质量评估 |
| GET | `/api/v1/ws/projects/:id/script-stream` | WebSocket：实时接收Agent输出流（SSE也可） |
| GET | `/api/v1/knowledge/hooks` | 钩子类型库（供前端浏览） |
| GET | `/api/v1/knowledge/narrative-structures` | 叙事结构库 |
| GET | `/api/v1/knowledge/cta-strategies` | CTA策略库 |
| GET | `/api/v1/knowledge/genre-conventions/:genre` | 垂类规范 |

### Step 8：前端页面实现

在 `apps/web/src/app/projects/[id]/` 下实现脚本创作工作台：

```
app/projects/[id]/
├── page.tsx                        # 项目概览/创意起点
├── ideate/
│   └── page.tsx                    # 灵感发散页
│       └── components/
│           ├── inspiration-form.tsx        # 灵感输入表单（支持输入一句话/上传参考视频/选垂类/选风格）
│           ├── creative-idea-card.tsx      # 创意想法卡片（10个方案并排展示）
│           ├── idea-compare.tsx            # 创意对比（选2-3个对比差异）
│           ├── random-catalyst-btn.tsx     # 🎲 随机灵感按钮（跨界/随机词）
│           └── hot-trend-badge.tsx         # 热点关联标签
├── script/
│   └── page.tsx                    # 脚本编辑页
│       └── components/
│           ├── script-editor.tsx           # 脚本编辑器（富文本，分beat块显示）
│           ├── hook-comparison.tsx         # 钩子候选对比
│           ├── beat-timeline.tsx           # Beat时间线（可视化脚本结构）
│           ├── emotion-curve-chart.tsx     # 情绪曲线图（recharts）
│           ├── script-score-card.tsx       # 质量评分雷达图
│           ├── compliance-alert.tsx        # 合规警告
│           ├── quick-fix-btn.tsx           # 一键优化按钮
│           └── natural-input-bar.tsx       # 底部自然语言修改输入框（类Copilot）
└── storyboard/
    └── page.tsx                    # 分镜编辑页
        └── components/
            ├── storyboard-table.tsx        # 分镜表格（TanStack Table + dnd-kit 拖拽排序）
            ├── shot-card.tsx               # 单镜头卡片（展开可编辑所有字段）
            ├── shot-inline-editor.tsx      # 内联编辑器
            ├── duration-indicator.tsx      # 时长指示器（是否超过目标时长）
            ├── shot-type-selector.tsx      # 景别可视化选择器（缩略图）
            ├── camera-movement-selector.tsx # 运镜选择器
            ├── ai-feasibility-badge.tsx    # AI可行性标签
            ├── regenerate-shot-btn.tsx     # 重新生成本镜按钮
            └── storyboard-summary.tsx      # 分镜概览（总时长/镜头数/平均镜头时长）
```

**交互设计核心要求**：

1. **灵感发散页的体验**：
   - 用户可以什么都不输入，直接点"🎲 给我灵感"，Agent会随机选一个垂类（基于用户历史或当前热点）给出10个方向
   - 10个创意方向以**卡片网格**排列，每张卡片有：创意标题、一句话描述、情绪emoji、可行性标签、"用这个"按钮
   - 用户可选择多个卡片"组合"（把创意A的钩子和创意B的叙事结合）
   - 每张卡片有"换一个类似的"按钮（保持方向不变，变体生成）
   - 展示"🔥基于当前热点"标签（关联热点的创意优先展示）

2. **脚本编辑页的体验**：
   - 脚本不是纯文本墙，而是按beat块分块展示（每个beat是一个卡片，标注名称、时长、情绪、功能）
   - 右侧有情绪曲线图+质量雷达图实时更新
   - 底部常驻一个**Copilot式输入框**："想改什么？直接说，比如'钩子更幽默点'/'缩短到30秒'/'加入一个反转'"
   - 合规警告以醒目的黄色/红色卡片出现在对应段落旁
   - 支持版本对比（side-by-side diff）

3. **分镜编辑页的体验**：
   - 表格视图：列=镜号/时长/景别/画面描述/台词/情绪，支持内联编辑
   - 拖拽镜头行可调整顺序，自动重排镜号
   - 顶部总时长条：直观显示是否超出目标时长
   - 每个镜头行有"AI难度"标签，红色的镜头给出警告和一键简化按钮
   - 批量操作：选中多个镜头，批量修改景别/光线/色调
   - "优化本镜"按钮：用自然语言说"让画面更有电影感"自动优化该镜描述

### Step 9：与前端Chat UI的深度集成

在Chat对话界面中，用户可以全程通过对话操作，不需要切换页面：
- "帮我想想做什么视频" → 触发Ideation Agent
- "第3个方向不错，但是我想更搞笑一点" → 变体生成
- "就用这个，写脚本" → 触发脚本Pipeline
- "钩子不够吸引人，换一个" → 钩子重生成
- "第5镜到第8镜改成快节奏蒙太奇" → 分镜修改
- "帮我把整体时长压到45秒" → 全局节奏调整
- "现在生成提示词" → 交给板块05的提示词引擎

Agent的思考过程（如"正在检索爆款库..."/"正在分析同类结构..."/"钩子专家正在设计3个候选...")要以柔和的灰色文字流式输出给用户，让用户感受到Agent在"思考"而不是在等。

## 质量保障

### Prompt版本管理
- 所有Agent的System Prompt严格版本化（与Mago现有SOP一致）
- 每个Agent维护固定测试集（20+case，覆盖主流垂类）
- 修改Prompt必须跑测试集，不允许退化
- 记录每次Prompt修改的效果变化（灰度→全量）

### 测试用例建设（必须实现）

在 `services/agent/tests/script/` 下编写自动化测试：
- `test_ideation.py`：给10种不同的模糊输入，验证ideation_agent能产出10个不同角度的创意，且每个创意有完整字段
- `test_hook_specialist.py`：测试钩子生成的多样性、字数控制、类型正确性
- `test_storyteller.py`：测试脚本结构完整性（有钩子/正文/CTA）、时长合理性
- `test_storyboard_agent.py`：测试分镜数量和时长分配符合目标、景别有变化、画面描述具象（不含抽象形容词，可用简单规则检测：不允许出现"很美""很伤心""很震撼"这类无具体信息的描述，必须有具体的视觉元素）
- `test_compliance.py`：植入10条违规文案，验证能被检测出
- `test_evaluator.py`：植入5个好脚本和5个差脚本，验证评估分数有显著区分度

### 测试集数据
创建 `services/agent/tests/data/script_test_cases.json`，包含至少30个测试case（每个垂类2-3个），每个case包含：
- input（用户原始输入）
- expected_hook_type（期望的钩子类型）
- expected_structure（期望的叙事结构）
- expected_shot_count_range（期望镜头数范围）
- forbidden_patterns（禁止出现的问题：如抽象描述词、极限词等）

## 验收标准

- [ ] 创意理论知识库6个JSON文件完整初始化：钩子(≥100种)、叙事结构(≥30种)、CTA(≥20种)、情绪曲线(≥15种)、垂类规范(≥20个)、节奏模式(≥10种)，每个条目有模板、示例、适用场景
- [ ] 8个Agent全部实现，System Prompt三层结构完整（宪法/流程/表达），每个Agent至少3个Few-shot示例
- [ ] 灵感发散Agent：输入一个模糊的"我想做美妆"，能输出10个角度差异明显的创意方向（测试验证差异度：创意名称/钩子类型/情绪基调至少两项不同）
- [ ] 跨领域创意激发算子至少实现5种（跨界移植/反转/极端化/代入/热梗嫁接）
- [ ] 完整的精细模式Happy Path走通：模糊输入→10个创意→选择一个→脚本→分镜，全程可在每个HITL节点自然语言修改
- [ ] 快速模式：输入一句话，3分钟内产出完整脚本+分镜（无需人工干预）
- [ ] 脚本评估Agent能对差脚本给出显著低分和具体改进建议
- [ ] 合规Agent能检测出植入的10种违规内容（极限词/医疗宣称等）
- [ ] 分镜画面描述具体可执行——随机抽取20个镜头，每个镜头描述都包含人物/动作/场景/光线/色调具体元素，不含"很XX"抽象词
- [ ] 前端灵感发散页/脚本编辑页/分镜编辑页完成，交互流畅
- [ ] 自然语言修改全链路可用（"钩子更幽默"/"缩短到30秒"/"第3镜换特写"能正确触发对应修改）
- [ ] 版本管理可用，可查看历史版本、回滚、diff对比
- [ ] WebSocket/SSE流式输出可用，用户能实时看到Agent思考过程
- [ ] `docs/research/03-script-studio.md` 有完整的GitHub调研结论
- [ ] `docs/dependencies.md` 更新
- [ ] `make lint && make test` 通过，脚本模块测试覆盖率≥70%
- [ ] ScriptPackage接口定义完整，可直接交给板块05的提示词引擎消费
