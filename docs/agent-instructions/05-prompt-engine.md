# 指令 05：提示词生成引擎（Prompt Engine）⭐ 最核心输出模块

## 角色设定

你是一名**顶级AI Prompt工程师+影视摄影指导(DP)+多模型专家**。你精通Midjourney/Stable Diffusion/Flux/Kling/Runway/Sora/Pika/Vidu/即梦/海螺/DALL-E等所有主流生图生视频模型的提示词语法、偏好词、能力边界和最佳参数。你的目标是构建一个**专业级提示词自动化工厂**——输入分镜脚本+角色卡+风格卡+目标模型，输出的提示词要达到**资深Prompt工程师手工调优30分钟**的水准，可直接粘贴到Mago或任何平台得到高质量结果。

## 前置依赖

必须完成：
- `01-project-bootstrap.md`（基础设施、Agent框架、LLM网关）
- `03-script-studio.md`（脚本和分镜数据，ScriptPackage接口）
- `04-character-style.md`（角色卡、风格卡、场景/道具数据）

## 核心价值主张

普通用户写的prompt："一个美女在咖啡馆喝咖啡，4k高清"（出图随机、一致性差、电影感全无）

**本引擎输出的prompt**（以Kling文生视频为例）：
```
一位25岁亚洲年轻女性，黑色中长发微卷，身穿米白色丝质衬衫佩戴细金项链（人物固定段），
坐在法式落地窗边的木质咖啡馆座位上，右手捧着白色陶瓷咖啡杯轻抿微笑，
窗外是秋日下午温暖的阳光透过百叶窗投射出条纹光影，桌上有打开的书和一小束干花，
中景镜头，略微俯视构图，浅景深f/1.8虚化背景，柔和自然侧光，
暖黄金秋色调，柯达Portra 400胶片质感，细腻颗粒感，
镜头缓缓推近（push in slow），窗帘微风轻拂动，咖啡热气袅袅升起，
4K分辨率，电影级调色，皮肤质感自然通透，细节精致，
8mm胶片颗粒，变形宽银幕镜头光晕

负向：模糊,变形手,畸形手指,多余肢体,低分辨率,水印,文字,Logo,过曝死白,噪点,蜡像感,不自然表情,面部扭曲,闪烁,画面抖动
参数：9:16竖屏 | 5秒 | 运动强度3 | FPS 24 | Seed: 48291（与同场景其他镜头同Seed区间）
参考图：[角色正面照] IP-Adapter权重0.8
连贯性：上一镜头(镜2)尾帧作为首帧参考
```

**区别在于**：结构化、细节丰富、专业术语准确、模型针对性优化、跨镜头一致性策略、参数完整、负向词覆盖常见AI缺陷。

## 执行步骤

### Step 1：调研GitHub与开源Prompt资源（必须！这是提示词质量的根基）

记录到 `docs/research/05-prompt-engine.md`。**提示词引擎的质量不取决于你的代码能力，而取决于你是否吸收了社区最优实践**，必须深度调研以下资源：

#### 1.1 模型官方文档与提示词指南
调研并提取每个模型的**官方提示词指南/最佳实践**：
- Midjourney: `midjourney.com/docs/...` (官方Prompting Guide、Parameter List、Cre/Sref/CW用法、Style References)
- Stable Diffusion: `Civitai` 热门作品的prompt规律、`SD WebUI` Wiki、`ComfyUI examples`、`civitai/SDXL_prompting_guide`
- Flux: Black Forest Labs官方文档、`civitai` Flux热门作品prompt分析
- Kling(可灵)：快手官方提示词指南、社区优质作品prompt案例
- Runway Gen-3/4：Runway官方Help Center的Prompt Guide、社区showcase
- Pika：Pika官方提示词指南、Discord优秀案例
- Sora：OpenAI官方Sora提示词指南、技术报告中提到的最佳实践
- DALL-E 3：OpenAI官方DALL-E提示词指南
- 即梦/海螺/通义万相/Vidu：各自官方文档和社区案例

#### 1.2 开源Prompt库/工具
搜索关键词：
- `awesome stable diffusion prompts github`
- `midjourney prompt generator open source`
- `prompt engineering library video generation github`
- `ComfyUI prompt helper`, `SD prompt generator`, `A1111 wildcards`
- `stable diffusion tag analyzer`, `danbooru tags wiki`

必须评估的项目：
- `adieyal/sd-dynamic-prompts`（⭐wildcards/组合生成，参考其语法思路）
- `Maks-s/sd-akashic`（SD知识库）
- `AUTOMATIC1111/stable-diffusion-webui` 中的prompt processing逻辑
- `pharmapsi/Prompt-Generator-for-Stable-Diffusion`（参考其词库组织方式）
- Civitai上的**优质模型/LoRA页面**（提取每个模型推荐的触发词和风格词）
- `Awesome-Prompt-Engineering` 等集合仓库中图像/视频生成部分

#### 1.3 电影摄影/镜头术语词表
- 搜索 `cinematography glossary github`, `camera shot list terminology`, `film lighting terms`
- 必须建立完整的中英文对照术语库（用户输入中文"推镜"→翻译成英文"slow push in"或中文对应专业词，根据模型偏好）
- 参考：`shotdeck.com`（专业镜头库）的标签体系，`shotlist.tumblr.com`等专业资源

#### 1.4 负面词库调研
- 搜索 `stable diffusion negative embedding`, `easynegative badhandv4`, `universal negative prompt`
- 参考：各模型社区分享的"通用负向词大全"
- 必须针对每个模型分别整理负面词（不同模型的"痛点"不同：SD手崩/多人混乱，视频模型闪烁/形变/脸部变化）

#### 1.5 输出物
调研后必须产出**两份核心资产**（不是写在文档里，要做成可被程序加载的JSON/文本文件）：

**A. 每个模型的能力画像文件**（`services/agent/src/knowledge/models/`）：
为每个适配模型创建一个JSON配置，例如 `kling-v3.json`：
```json
{
  "model_id": "kling-v3",
  "model_name": "可灵3.0",
  "vendor": "kuaishou",
  "version": "3.0",
  "capabilities": {
    "text_to_image": true,
    "image_to_image": true,
    "text_to_video": true,
    "image_to_video": true,
    "reference_face": true,
    "reference_pose": false,
    "motion_brush": true,
    "max_video_duration": 120,
    "supported_resolutions": ["720p", "1080p"],
    "supported_aspect_ratios": ["9:16", "16:9", "1:1", "4:3", "3:4"],
    "supports_seed": true,
    "supports_negative_prompt": true,
    "max_prompt_length_chars": 800
  },
  "prompt_preferences": {
    "language": "zh-CN",           // 偏好语言
    "style": "natural_language",    // 自然语言或标签式
    "sentence_structure": "主体+动作+场景+镜头+光影+色调+画质",
    "separator": "，",
    "weight_syntax": null,          // 是否支持权重语法（如 (word:1.2)）
    "effective_keywords": [...],    // 经验证有效的关键词（从优秀案例中提取）
    "ineffective_keywords": [...],  // 无意义/反效果词
    "motion_keywords_effective": true,  // 运动描述是否有效
    "camera_keywords_effective": true
  },
  "strengths": ["写实画面", "人物一致性", "复杂动作"],
  "weaknesses": ["手部精细动作偶尔有瑕疵", "文字生成不可靠"],
  "positive_template_file": "kling-v3-positive.txt",
  "negative_template_file": "kling-v3-negative.txt",
  "default_parameters": {
    "duration": 5,
    "fps": 24,
    "aspect_ratio": "9:16",
    "motion_strength": 5,
    "cfg_scale": 7,
    "seed_strategy": "random",
    "negative_prompt_enabled": true
  },
  "parameter_ranges": {
    "duration": [3, 120],
    "motion_strength": [0, 10],
    "cfg_scale": [1, 20]
  },
  "consistency_strategies": {
    "seed_locking": "建议同场景相邻镜头使用连续seed",
    "reference_image": "支持首帧参考，IP-Adapter权重建议0.7-0.9",
    "face_stability": "角色描述段保持完全一致"
  },
  "known_bad_cases": [
    {"issue": "手部多指/变形", "workaround": "加入负向词，避免给手部复杂动作，或局部inpainting"},
    {"issue": "画面闪烁", "workaround": "降低motion_strength，使用首帧参考，加强主体描述"}
  ],
  "quality_booster_suffix": "4K分辨率,电影级画质,细节丰富,精致构图",
  "best_practices_md": "..."
}
```

**首期必须适配的模型列表（至少12个）**：
1. `midjourney-v6.1`（文生图，含Niji 6单独配置）
2. `midjourney-v7`（最新版）
3. `sdxl-1.0`（Stable Diffusion XL）
4. `flux-dev` / `flux-schnell`
5. `kling-v3`（可灵3.0）
6. `jimeng-2.0`（即梦）
7. `runway-gen4`（Runway Gen-4）
8. `pika-2.0`
9. `sora-turbo`
10. `vidu-2.0`
11. `hailuo-v1`（海螺MiniMax）
12. `wanx-2.1`（通义万相）
13. `dalle-3`（DALL-E 3）

**B. 每个模型的正负向提示词模板文件**（`templates/`目录下）：
每个模型配置一个 `.txt` 的Jinja2模板文件，定义prompt组装结构。例 `kling-v3-positive.j2`：
```jinja
{# Kling 3.0 文生视频正向提示词模板 #}
{# 主体段（含角色固定描述）#}{{ subject_description }}{% if character_fragment %}，{{ character_fragment }}{% endif %}{% if props %}，{{ props | join('，') }}{% endif %}，
{# 场景环境段 #}{{ scene_environment }}{% if time_of_day %}，{{ time_of_day }}{% endif %}{% if weather %}，{{ weather }}{% endif %}，
{# 镜头语言段 #}{{ shot_type_cn }}，{% if camera_movement %}镜头{{ camera_movement_cn }}，{% endif %}{% if camera_angle %}{{ camera_angle_cn }}，{% endif %}{% if depth_of_field %}{{ depth_of_field_cn }}，{% endif %}
{# 光影色调段 #}{{ lighting_description }}{% if color_tone %}，{{ color_tone }}{% endif %}{% if style_fragment %}，{{ style_fragment }}{% endif %}，
{# 运动描述段（视频专用）#}{% if motion_description %}{{ motion_description }}，{% endif %}
{# 画质增强段 #}{{ quality_booster }}{% if extra_quality_keywords %}，{{ extra_quality_keywords | join('，') }}{% endif %}
```

### Step 2：数据库表设计

```sql
-- 提示词包（一个分镜对应一个提示词包，包含多个模型版本）
CREATE TABLE prompt_packages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    storyboard_id UUID NOT NULL REFERENCES storyboards(id) ON DELETE CASCADE,
    version INT NOT NULL DEFAULT 1,
    name VARCHAR(255),
    status VARCHAR(20) DEFAULT 'draft',   -- draft/ready/exported/used
    total_shots INT,
    selected_models VARCHAR(32)[],         -- 用户选定要输出的模型ID列表
    global_parameters JSONB DEFAULT '{}',  -- 全局参数覆盖
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_prompt_pkg_project ON prompt_packages(project_id);
CREATE INDEX idx_prompt_pkg_storyboard ON prompt_packages(storyboard_id);

-- 单条提示词（一个镜头+一个模型=一条prompt）
CREATE TABLE prompts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    package_id UUID NOT NULL REFERENCES prompt_packages(id) ON DELETE CASCADE,
    shot_id UUID NOT NULL REFERENCES storyboard_shots(id) ON DELETE CASCADE,
    model_id VARCHAR(64) NOT NULL,         -- kling-v3/midjourney-v7/...
    prompt_type VARCHAR(16) NOT NULL,      -- image/video
    -- 提示词内容
    positive_prompt TEXT NOT NULL,
    negative_prompt TEXT,
    parameters JSONB DEFAULT '{}',         -- {duration, aspect_ratio, fps, cfg_scale, seed, motion_strength, ...}
    -- 参考资源
    reference_images JSONB DEFAULT '[]',   -- [{url, role: "face"|"style"|"first_frame"|"last_frame", weight: 0.8}]
    lora_triggers JSONB DEFAULT '[]',      -- [{name, trigger_words, weight}]
    -- 一致性策略
    seed_value INT,
    seed_locked BOOLEAN DEFAULT false,
    consistency_notes TEXT,
    -- 版本与迭代
    version INT NOT NULL DEFAULT 1,
    parent_prompt_id UUID REFERENCES prompts(id),
    iteration_note TEXT,                   -- 本轮修改说明
    -- 质量评分
    quality_score JSONB DEFAULT '{}',      -- {completeness:9, specificity:8, model_fit:9, consistency:7, feasibility:7}
    quality_feedback JSONB DEFAULT '[]',
    -- 导出与使用
    exported_to_mago BOOLEAN DEFAULT false,
    mago_task_id UUID,
    user_modified BOOLEAN DEFAULT false,
    created_by VARCHAR(16) DEFAULT 'agent', -- agent/user
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_prompts_package ON prompts(package_id);
CREATE INDEX idx_prompts_shot ON prompts(shot_id);
CREATE INDEX idx_prompts_model ON prompts(model_id);

-- 提示词迭代历史（记录每次优化）
CREATE TABLE prompt_iterations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    prompt_id UUID NOT NULL REFERENCES prompts(id) ON DELETE CASCADE,
    iteration_no INT NOT NULL,
    user_feedback TEXT,                    -- 用户反馈原文
    changes_made JSONB DEFAULT '[]',       -- [{field, old_value, new_value, reason}]
    before_positive TEXT,
    after_positive TEXT,
    score_before JSONB,
    score_after JSONB,
    agent_id VARCHAR(64),                  -- 哪个Agent做的修改
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 模型配置表（可动态更新，不硬编码）
CREATE TABLE model_configs (
    id VARCHAR(64) PRIMARY KEY,            -- kling-v3
    name VARCHAR(128) NOT NULL,
    vendor VARCHAR(64),
    capabilities JSONB NOT NULL,
    prompt_preferences JSONB,
    default_parameters JSONB,
    parameter_ranges JSONB,
    quality_booster TEXT,
    negative_boilerplate TEXT,
    template_positive TEXT,                -- Jinja2模板存储在DB或文件系统
    template_negative TEXT,
    consistency_strategies JSONB,
    known_limitations JSONB,
    best_practices TEXT,
    is_active BOOLEAN DEFAULT true,
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- LoRA/模型推荐库
CREATE TABLE lora_recommendations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    model_id VARCHAR(64) NOT NULL,          -- 适用哪个基础模型
    name VARCHAR(255) NOT NULL,
    lora_source VARCHAR(64),                -- civitai/liblib/huggingface/...
    source_url TEXT,
    trigger_words TEXT[],
    recommended_weight FLOAT,
    category VARCHAR(64),                   -- style/character/concept/pose/background
    description TEXT,
    preview_url TEXT,
    positive_keywords TEXT[],               -- 触发该风格应加的关键词
    negative_keywords TEXT[],
    usage_count INT DEFAULT 0,
    is_verified BOOLEAN DEFAULT false,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_lora_model ON lora_recommendations(model_id);
CREATE INDEX idx_lora_category ON lora_recommendations(category);

-- 专业术语词典（中英对照+同义词）
CREATE TABLE prompt_terms (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    term_cn VARCHAR(128) NOT NULL,
    term_en VARCHAR(128),
    category VARCHAR(32) NOT NULL,          -- shot_type/camera_movement/lighting/color/style/emotion/quality
    synonyms_cn TEXT[],
    synonyms_en TEXT[],
    description TEXT,
    prompt_fragment_cn TEXT,               -- 用于中文模型
    prompt_fragment_en TEXT,               -- 用于英文模型
    applicable_models VARCHAR(64)[],        -- 在哪些模型上有效（空=全部）
    example_usage TEXT,
    is_core BOOLEAN DEFAULT false,         -- 核心术语（必会）
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_prompt_terms_category ON prompt_terms(category);
```

### Step 3：专业术语翻译/映射引擎

这是一个**关键细节**：分镜师Agent产出的是标准化中文术语（如"推镜"、"伦勃朗光"、"特写"），但不同模型偏好的语言和术语不同。需要一个术语映射层：

在 `services/agent/src/prompt_engine/terminology.py` 实现：
- `translate_term(term_cn: str, model_id: str) -> str`: 根据模型偏好返回中文或英文的最有效prompt词汇
  - "推镜" → 中文模型："镜头缓慢推近"；英文模型："slow push in, dolly forward"
  - "特写" → 中文模型："特写镜头，面部细节"；英文模型："extreme close-up shot, ECU, detailed facial features"
- `build_shot_descriptor(shot: ShotForPrompt, model_id: str) -> dict`: 将分镜字段批量翻译为模型友好的描述片段
- 术语词典从 `prompt_terms` 表加载，启动时缓存，支持热更新

首期必须建立至少**300+条专业术语**（seed到数据库）：
- 景别术语：10种+
- 运镜术语：20种+
- 角度术语：10种+
- 光影术语：30种+
- 色调术语：30种+
- 画质/胶片术语：30种+
- 构图术语：15种+
- 情绪/氛围术语：40种+
- 动作/运动术语：50种+
- 视频特有术语（闪烁/抖动/稳定性/帧）：30种+
- 导演风格术语：30种+

### Step 4：提示词组装核心引擎

在 `services/agent/src/prompt_engine/` 下实现：

```
prompt_engine/
├── __init__.py
├── assembler.py              # 提示词组装核心
├── terminology.py            # 术语翻译/映射
├── model_registry.py         # 模型配置加载/管理
├── template_engine.py        # Jinja2模板渲染
├── consistency.py            # 跨镜头一致性逻辑
├── quality_checker.py        # 提示词质量检查
├── parameter_advisor.py      # 参数建议
├── negative_builder.py       # 负向词组装
├── lora_recommender.py       # LoRA推荐
├── seed_strategy.py          # Seed策略
└── reference_image_manager.py
```

#### 4.1 组装主逻辑（assembler.py）

核心函数 `assemble_prompt(shot, character, style, scene, model_config, global_context) -> PromptResult`：

输入：单镜头数据(ScriptPackage.ShotForPrompt) + 角色卡 + 风格卡(含组合) + 场景/道具 + 模型配置 + 全局上下文（前后镜头、总时长、平台）

组装步骤（严格按顺序）：

**Step A：准备片段**
1. **主体段**：`character.prompt_fragment`（如果有角色卡）+ `shot.subject_description`（当前镜头动作/表情）+ 道具描述
2. **场景段**：`scene.prompt_fragment`（如果有预置场景）+ `shot.scene_environment` + 时间/天气
3. **镜头语言段**：术语映射后的景别+运镜+角度+景深+焦距+构图
4. **光影段**：`shot.lighting` + 风格卡的lighting
5. **色调/风格段**：`merged_style.positive_fragment`（风格卡组合后的正向片段）+ `shot.color_tone`
6. **运动描述段**（仅视频类型）：主体运动+镜头运动+环境运动，详细时序列举
7. **画质增强段**：模型配置的 `quality_booster` + 分辨率/细节/质感关键词
8. **LoRA触发词段**：根据风格/场景推荐的LoRA触发词

**Step B：渲染模板**
- 将上述片段填入对应模型的Jinja2模板
- 注意片段顺序（不同模型对词序敏感度不同：MJ是越靠前权重越高，SD类标签式对顺序不敏感但开头词更重要）
- 处理分隔符（中文逗号/英文逗号/空格/标签式逗号）

**Step C：负向词组装（negative_builder.py）**
- 基础层：通用负向词（低质量/变形/水印/模糊）
- 模型层：该模型的negative_boilerplate（如SD常用"EasyNegative"等，视频模型的"闪烁/抖动"）
- 场景层：特定场景的负向词（人像加"畸形手指/不对称眼"，美食加"不真实塑料感"等）
- 角色层：`character.negative_fragment`
- 风格层：`merged_style.negative_fragment`
- 合并去重，按模型语法格式化

**Step D：参数建议（parameter_advisor.py）**
- 读取模型默认参数
- 根据目标平台/时长/比例调整（如抖音默认9:16，B站默认16:9）
- 根据镜头类型微调（运动镜头motion_strength调高，静态镜头调低）
- 根据用户选择覆盖

**Step E：一致性策略（consistency.py）**
- 为同角色/场景镜头规划seed：同一分镜内的同角色镜头使用seed_base到seed_base+N的连续seed
- 相邻镜头标记首尾帧建议（"上一镜头尾帧作为首帧"）
- FaceID/IP-Adapter参考图设置（角色卡中的参考图自动填入reference_images）
- 风格参考图设置（风格卡的example_image作为sref）
- 写出consistency_notes（文字描述一致性策略，给用户看）

**Step F：长度检查与裁剪**
- 检查prompt长度是否超过模型限制
- 超长时按优先级裁剪：先削画质词，再削环境细节，保留主体/动作/风格核心段
- 长度接近上限时警告用户

**Step G：质量自检（quality_checker.py）**
- 完整性检查：是否包含主体/动作/场景/镜头/光影/风格/画质各段
- 具体性检查：是否包含抽象空洞词（"很美""很震撼""非常好看"这类无视觉信息的词 → 警告或替换）
- 模型适配检查：是否使用了该模型不支持的语法（如在Kling里用(MJ:1.2)权重）
- 一致性风险检查：是否有与上一镜头矛盾的描述
- 可行性检查：检测AI难生成的元素（多人精确互动/文字/复杂手指动作/物理复杂交互），给出warning和替代方案建议
- 输出评分和改进建议（低于阈值自动触发重写）

#### 4.2 跨镜头一致性算法（consistency.py）

这是视频质量的关键，必须实现至少5种一致性策略：

1. **角色描述锁**：所有涉及同一角色的镜头，角色描述段使用完全相同的字符串（从角色卡prompt_fragment复制，不允许各镜头Agent修改）
2. **Seed区间锁**：为同一场景/连续镜头分配连续seed值（如镜1:10001, 镜2:10002, 镜3:10003），利用潜空间连续性
3. **首尾帧链式引用**：除第一镜外，每镜建议用上一镜的尾帧作为首帧参考
4. **风格全局锁**：style_fragment在所有镜头保持一致，只有单镜头特殊要求时追加
5. **色调/光线连贯**：相邻镜头的光线方向和色调不突变（除非脚本要求，如"突然切换到黑暗"），相邻镜头光线一致性评分低于阈值时警告

同时检测一致性冲突：
- 镜3描述"穿着白色衬衫"而角色卡是红色裙 → 标记冲突
- 镜2是"白天阳光"镜3突然变成"夜晚"（脚本没有要求时间变化）→ 标记
- 同一人物在相邻镜头发型/年龄描述变化 → 标记

### Step 5：文生图 vs 文生视频提示词差异化处理

#### 文生图提示词特点：
- 强调静态细节（材质、纹理、光影细节、分辨率）
- 需要构图完整（因为是单帧）
- 负面词重点在解剖错误（手指/肢体/面部）
- 支持LoRA触发词、ControlNet建议
- MJ类模型需要--ar/--s/--cref/--sref参数，SD类需要采样器/步数/CFG

#### 文生视频提示词特点：
- **运动描述是灵魂**：必须有主体运动+镜头运动+环境运动三要素
- 描述要有**时序感**：动作有起点终点、有过渡
- 避免静态堆叠词（"站在树下微笑"vs"微笑着从树下走向镜头，头发随风飘动"）
- 负面词重点在**时间一致性问题**（闪烁flickering、变形warping、脸部突变face morphing、颜色跳变color shifting、时间不连贯temporal inconsistency）
- 运动幅度参数（motion_strength/camera_noise）要根据镜头类型建议
- Kling/Pika要建议Motion Brush区域（可选高级功能）
- Sora/Runway类英文模型偏好剧本式完整句子，而非标签堆叠

在 `assembler.py` 中通过 `prompt_type`（image/video）参数分支处理，使用不同模板和增补逻辑。

### Step 6：提示词优化Agent（迭代优化）

在 `services/agent/src/agents/prompt/optimizer.py` 实现：

**输入**：当前Prompt + 用户反馈（自然语言）或生成结果图片/视频URL + 问题描述
**输出**：优化后的Prompt + 修改说明

常见优化场景的处理逻辑：

| 用户反馈/问题 | 定位段落 | 修改策略 |
|:---|:---|:---|
| "角色脸变了/不像" | 主体段+一致性 | 加强角色描述、增加FaceID权重、锁定seed、加"same face as previous"类提示 |
| "画面太暗/太亮" | 光影段 | 调整光线描述（增加"brightly lit"/"overexposed"修正/加HDR） |
| "风格不对，没有电影感" | 风格段 | 追加电影风格词（cinematic, 2.39:1, anamorphic lens, film grain, color grading） |
| "动作不自然/僵硬" | 运动段 | 简化复杂动作、加"natural motion, fluid movement, smooth" |
| "画质不够清晰" | 画质段 | 加4K/8K/masterpiece/high detail/sharp focus类词，排除"blurry, out of focus"负向词 |
| "手崩了/多手指" | 主体+负向 | 加"hands behind back/pockets/hidden"避坑或在负向词强化deformed hands, extra fingers |
| "闪烁/抖动"（视频） | 运动段+负向 | 降低motion_strength、加"stable, no flicker, temporal consistency, smooth motion" |
| "画面太乱/元素太多" | 场景段 | 简化场景描述、删除冗余元素、加"minimal composition, clean background, shallow depth of field" |
| "没有氛围感/太平" | 光影+色调+情绪 | 加体积光/雾气/颗粒感/色调调整，强调emotion词 |

**迭代策略**：
- 每次迭代只改2-3个变量，避免大改
- 记录每次修改的字段、旧值、新值、原因（存入prompt_iterations表）
- 连续3次迭代未改善 → 提示用户可能需要换模型或修改分镜内容
- 积累Bad Case库："问题类型→成功修改方案"映射，后续遇到类似问题自动套用

### Step 7：提示词评分Agent

在 `services/agent/src/agents/prompt/reviewer.py`：

对每条生成的prompt进行7维评分（每项1-10）：
1. **完整性**（completeness）：主体/动作/场景/镜头/光影/风格/画质各段是否齐全
2. **具体性**（specificity）：描述是否具象可执行，不含模糊空洞词
3. **模型适配度**（model_fit）：语法/词序/语言是否符合模型偏好
4. **一致性风险**（consistency）：与上一镜头/角色卡/风格卡是否冲突
5. **安全合规**（compliance）：是否有敏感/违规内容
6. **生成可行性**（feasibility）：AI是否能生成该描述
7. **专业度**（professionalism）：术语使用是否准确、是否符合影视/摄影专业表达

**评分方法**：
- 规则检测（30%权重）：抽象词检测、必填段检测、长度检测、语法检测、负面词覆盖检测
- LLM评分（70%权重）：将prompt+模型信息+评分标准发给LLM，用function_calling输出结构化评分+改进建议
- 综合得分 < 7分或任一维度 < 5分 → 自动优化一轮，附具体改进建议

### Step 8：多模型一键转换

用户在UI上切换目标模型时，同一条分镜的提示词自动重新生成适配版本。实现：
- 保持语义不变，仅变换：语言（中↔英）、词序、结构、参数、负面词、LoRA建议
- 提供"对比视图"：同一镜头不同模型的prompt并排展示
- 支持"批量适配"：一键把整个分镜包适配为多个模型版本（如同时生成Kling+Runway+MJ版本）

### Step 9：导出与Mago集成

导出格式支持：
1. **单条复制**：点击镜头卡片上的"复制"按钮，复制正向词/负向词/参数到剪贴板
2. **批量导出**：
   - JSON：结构化完整数据，供程序调用
   - CSV/Excel：表格形式，每行一个镜头（方便人工管理）
   - Markdown：格式化文档，适合归档
   - **ComfyUI工作流JSON**（高级）：直接生成可导入ComfyUI的workflow JSON，预填prompt和参数
3. **推送到Mago**（核心集成）：
   - 调用Mago API，为每个镜头创建生图/生视频任务
   - 自动上传角色参考图作为FaceID/reference
   - 正确传递参数（时长/比例/分辨率/motion_strength/seed）
   - 获取Mago任务ID，回写到prompts表
   - 轮询或回调获取生成结果，在前端展示
   - 结果不满意：点击"优化提示词"→optimizer agent基于结果图优化→重新推送
4. **复制为模板**：将满意的提示词保存为自定义模板，未来类似场景一键应用

### Step 10：API实现

| 方法 | 路径 | 功能 |
|:---|:---|:---|
| POST | `/api/v1/storyboards/:id/prompt-packages` | 创建提示词包（指定目标模型列表，触发生成） |
| GET | `/api/v1/prompt-packages/:id` | 提示词包详情 |
| GET | `/api/v1/prompt-packages/:id/prompts` | 包内所有提示词（按镜头/模型筛选） |
| GET | `/api/v1/prompts/:id` | 单条提示词详情 |
| PUT | `/api/v1/prompts/:id` | 手动修改提示词（用户编辑） |
| POST | `/api/v1/prompts/:id/optimize` | 触发优化（接收自然语言反馈或结果分析） |
| POST | `/api/v1/prompts/:id/remodel` | 切换模型重新生成提示词 |
| POST | `/api/v1/prompt-packages/:id/batch-remodel` | 批量切换模型（整个包） |
| POST | `/api/v1/prompts/:id/export/clipboard` | 复制（返回格式化文本） |
| POST | `/api/v1/prompt-packages/:id/export/:format` | 导出（json/csv/md/comfyui） |
| POST | `/api/v1/prompt-packages/:id/send-to-mago` | 一键推送到Mago生成 |
| GET | `/api/v1/prompts/:id/mago-result` | 获取Mago生成结果 |
| POST | `/api/v1/prompts/:id/regenerate-after-result` | 基于结果图优化重发 |
| GET | `/api/v1/model-configs` | 获取可用模型列表及配置 |
| GET | `/api/v1/prompt-terms` | 术语库查询 |
| GET | `/api/v1/lora-recommendations` | LoRA推荐（按模型/风格/场景） |

### Step 11：前端实现

在 `apps/web/src/app/projects/[id]/prompts/` 下：

```
app/projects/[id]/prompts/
├── page.tsx                        # 提示词包总览页
├── [packageId]/
│   └── page.tsx                    # 提示词包详情页
│       └── components/
│           ├── model-selector.tsx          # 模型选择器（多选chip，显示模型logo）
│           ├── prompt-shot-card.tsx        # 单镜头提示词卡片（核心组件）
│           ├── prompt-text-editor.tsx      # 提示词文本编辑器（可手动修改+语法高亮）
│           ├── negative-prompt-section.tsx # 负向词区域
│           ├── parameter-panel.tsx         # 参数面板（可视化滑杆调CFG/motion_strength/seed等）
│           ├── reference-image-panel.tsx   # 参考图管理区（FaceID/Style/首帧/尾帧）
│           ├── consistency-badge.tsx       # 一致性标签（seed锁/角色锁/风格锁）
│           ├── quality-score-ring.tsx      # 质量分环形图
│           ├── optimize-input.tsx          # 自然语言优化输入框
│           ├── copy-prompt-btn.tsx         # 一键复制按钮
│           ├── send-to-mago-btn.tsx        # 推送到Mago按钮
│           ├── result-preview.tsx          # Mago生成结果展示
│           └── model-compare-view.tsx      # 多模型对比视图（同一镜头不同prompt并排）
└── components/
    ├── batch-export-dialog.tsx     # 批量导出弹窗
    └── comfyui-export-wizard.tsx   # ComfyUI导出向导（高级用户）
```

**UI/UX核心要求**：
1. **提示词卡片设计**：每张镜头卡片紧凑展示正向词（大段）、负向词（可折叠）、参数（小标签）、质量分（小圆环），不臃肿
2. **一键复制**：正向词、负向词、完整命令（含参数）分别有独立复制按钮，复制成功有toast提示
3. **可视化参数调节**：参数不是显示JSON，而是滑杆+数值+说明文字（"运动幅度：3 → 小幅运动，适合静态讲解"）
4. **质量分实时显示**：右侧/右上角有小圆环显示总分，hover显示各维度分
5. **Mago结果集成**：推送到Mago后卡片内直接显示生成结果缩略图，点击放大，不满意有"🔄优化重生成"按钮
6. **批量操作**：顶部工具栏支持"全部复制"、"全部推送到Mago"、"批量切换模型"
7. **一致性标记**：保持seed锁定的镜头有🔒seed锁图标，角色一致镜头有👤图标，风格一致有🎨图标，鼠标悬停显示具体说明
8. **进度状态**：提示词生成过程中显示进度（"正在生成镜1-3..."/"正在优化镜5...")

### Step 12：集成到LangGraph总流程

在 `services/agent/src/core/graph.py` 中新增节点：
- `prompt_generation`：接收ScriptPackage，为所有镜头所有选中模型生成提示词
- `prompt_qa`：质量评分，低分自动重生成
- 输出节点：提示词包就绪，等待用户审核/导出/推送Mago

用户在Chat中可以说：
- "生成提示词，用可灵3.0" → 触发prompt_generation节点（仅kling-v3）
- "适配成Midjourney和Runway版本" → 触发remodel
- "第3镜的提示词加一点电影感" → 触发optimizer
- "全部推送到Mago" → 批量发送
- "画质不行，优化一下" → 基于Mago返回结果自动优化

## 测试要求

必须实现的测试：
1. **模型配置完整性测试**：每个模型JSON必填字段齐全
2. **模板渲染测试**：用标准测试数据渲染每个模型的模板，输出无空字段、无Jinja2语法错误
3. **术语映射测试**：300条术语在12个模型上都能正确翻译
4. **一致性测试**：构造一个10镜分镜（同角色同场景），验证seed连续、角色描述完全一致、风格片段一致
5. **负向词覆盖测试**：人像类prompt负向词必须包含"deformed hands/malformed limbs"等
6. **长度裁剪测试**：超长输入时裁剪策略保留核心段
7. **质量评分测试**：植入5条明显差的prompt（抽象词/缺字段/模型语法错），评分必须低于阈值
8. **优化器测试**：给一个有明确问题的prompt（无光影描述）+ 反馈"加光影"，验证优化器正确修改对应段落
9. **端到端测试**：输入一个完整ScriptPackage，验证为12个模型产出的prompt可直接使用（至少结构完整、参数合法）

测试数据文件：`services/agent/tests/prompt_engine/test_packages/` 下存放5个标准分镜测试用例（不同类型：口播/美妆/剧情/风景/产品），每个用例包含输入ScriptPackage和预期prompt要点断言。

## 验收标准（最高标准，因为这是核心输出模块）

- [ ] 12个模型的配置文件齐全（JSON），positive/negative模板编写完成，质量booster和negative boilerplate经过专业验证
- [ ] 300+专业术语库完整，每个术语有中/英对照和模型特定的prompt片段
- [ ] 提示词组装引擎完成，支持image/video两种prompt类型
- [ ] 5种一致性策略全部实现（角色锁/seed锁/首尾帧/风格锁/色调连贯）
- [ ] 跨镜头一致性冲突检测可用
- [ ] 负向词分层组装正确（通用/模型/场景/角色/风格五层）
- [ ] 质量评分Agent 7维评分可用，差prompt能识别
- [ ] 提示词优化Agent能处理10类常见问题
- [ ] 多模型一键切换/对比可用
- [ ] Mago API对接完成，一键推送+结果回传+闭环优化
- [ ] 导出格式：JSON/CSV/Markdown/ComfyUI/复制 全部可用
- [ ] 前端提示词卡片UI美观、功能完整（复制/编辑/参数调节/优化/推送Mago/查看结果）
- [ ] 多模型对比视图可用
- [ ] 预置LoRA推荐库（初版至少50个热门LoRA，跨主流模型）
- [ ] **真人抽检**：从测试集随机取20条prompt，由资深Prompt工程师（或你作为Agent自检）按A/B/C/D评级，A级（直接可用）≥60%，A+B级≥90%，无D级
- [ ] `docs/research/05-prompt-engine.md` 中调研记录完整，包含对每个模型官方文档/社区实践的引用
- [ ] `docs/dependencies.md` 更新
- [ ] `make lint && make test` 通过，测试覆盖率≥80%（核心模块）
