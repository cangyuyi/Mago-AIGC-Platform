# 指令 04：角色与风格管理中心（Character & Style）

## 角色设定

你是一名**视觉概念设计师+IP形象顾问+Prompt工程师**，擅长角色设计、视觉风格定义、以及将视觉概念转化为AI生图/生视频可识别的专业提示词片段。你理解FaceID/IP-Adapter/LoRA/Reference模型的技术参数，也理解视觉美学的专业知识（摄影/电影/美术/色彩理论）。

## 前置依赖

- 必须先完成 `01-project-bootstrap.md`
- 建议先完成 `03-script-studio.md`（会使用Character/Style类型）

## 任务目标

构建角色卡系统和风格卡系统，使用户可以：
1. 通过文字描述或上传参考照片，创建可跨镜头/跨项目复用的角色形象
2. 选择/组合视觉风格（光影/色调/镜头/导演风格）形成风格卡
3. 管理场景、道具、品牌视觉规范等可复用资产
4. 在脚本→分镜→提示词全链路中自动引用这些资产，**确保跨镜头、跨视频的一致性**

## 执行步骤

### Step 1：调研GitHub开源方案（必须）

记录到 `docs/research/04-character-style.md`：

1. **IP-Adapter / FaceID 参考实现**：
   - 搜索关键词：`IP-Adapter FaceID github`, `instantID face consistency`, `photo maker character consistency`, `PuLID face`
   - 参考：`tencent-ailab/IP-Adapter`(⭐腾讯官方), `InstantID/InstantID`(单图面部保持), `SHYuanBest/PhotoMaker`(微软,可学习ID)
   - 目标：理解这些技术的最佳参数（权重范围、参考图要求），将参数建议内置到角色卡中

2. **AI形象/头像生成开源方案**：
   - 搜索关键词：`AI avatar generator open source github`, `virtual character creator`
   - 参考：`humanova/avatargen` 等，主要参考其角色属性定义（发型/脸型/肤色/服装等维度划分）
   - 决策：不引入重型生成器，只借鉴角色属性分类体系

3. **色彩理论与调色LUT数据**：
   - 搜索关键词：`color grading LUT free download`, `cinematic color palette dataset`, `film color science github`
   - 参考：`color-science/colour`(色彩科学Python库), `hailiang/colorweave`(调色板生成)
   - 决策：预置20+电影级调色方案（描述+hex色板+LUT名称），在风格卡中引用

4. **React颜色选择器/图片上传组件**：
   - 搜索：`react color picker`, `react image upload crop`, `react dropzone`
   - 参考：`react-dropzone`(文件上传), `react-image-crop`(图片裁剪), `react-colorful`(颜色选择)

### Step 2：数据库表设计

```sql
-- 角色卡表
CREATE TABLE characters (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    owner_id UUID NOT NULL REFERENCES users(id),
    org_id UUID REFERENCES organizations(id),
    visibility VARCHAR(16) DEFAULT 'private',  -- private/org/public
    name VARCHAR(128) NOT NULL,
    description TEXT,
    -- 基础属性
    gender VARCHAR(16),                       -- male/female/non-binary/unknown
    age_appearance VARCHAR(16),               -- child/teen/young_adult/adult/middle_aged/senior
    ethnicity VARCHAR(32),                    -- asian/white/black/latino/middle_eastern/south_asian/mixed
    -- 详细视觉描述（用于提示词）
    face_description TEXT,                    -- 面部详细描述
    hair_description TEXT,                    -- 发型发色
    body_description TEXT,                    -- 体型
    clothing_default TEXT,                    -- 默认服装描述
    skin_details TEXT,                        -- 皮肤细节（痣/疤痕/肤色）
    distinctive_features TEXT[],             -- 标志性特征（眼镜/痣/纹身/配饰）
    personality_vibe VARCHAR(128),            -- 气质关键词（温柔/干练/冷酷/可爱/知性…）
    -- AI生成参数建议
    faceid_weight FLOAT DEFAULT 0.8,          -- FaceID/IP-Adapter建议权重
    ip_adapter_scale FLOAT DEFAULT 0.7,
    reference_strategy VARCHAR(32) DEFAULT 'faceid',  -- faceid/instantid/photo_maker/description_only
    seed_base INT,                            -- 建议基础seed（同角色跨镜头锁定seed区间）
    -- 适配模型（哪些模型有该角色的适配参数）
    model_compatibility JSONB DEFAULT '{}',    -- {"kling-v3": {"seed": 12345, "weight": 0.8}, "midjourney": {"cref": "url", "cw": 100}}
    prompt_fragment TEXT,                     -- 自动生成的、嵌入每个镜头prompt的固定角色描述段
    negative_fragment TEXT,                   -- 针对该角色的负向词片段
    tags TEXT[],
    is_preset BOOLEAN DEFAULT FALSE,          -- 是否平台预置角色
    usage_count INT DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_characters_owner ON characters(owner_id);
CREATE INDEX idx_characters_org ON characters(org_id);

-- 角色参考图片表
CREATE TABLE character_ref_images (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    character_id UUID NOT NULL REFERENCES characters(id) ON DELETE CASCADE,
    image_type VARCHAR(32) NOT NULL,          -- front_face/side_face/half_body/full_body/expression_sheet/clothing_ref
    image_url TEXT NOT NULL,                  -- MinIO URL
    thumbnail_url TEXT,
    width INT,
    height INT,
    ai_description TEXT,                      -- AI多模态分析生成的描述
    embedding vector(512),                    -- CLIP embedding（用于相似角色检索）
    sort_order INT DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_char_images_char ON character_ref_images(character_id);

-- 风格卡表
CREATE TABLE style_presets (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    owner_id UUID REFERENCES users(id),
    org_id UUID REFERENCES organizations(id),
    visibility VARCHAR(16) DEFAULT 'private',
    name VARCHAR(128) NOT NULL,
    category VARCHAR(32) NOT NULL,            -- visual_style/lighting/color_grading/lens/director/cinematography/brand
    description TEXT,
    -- 提示词片段
    positive_fragment TEXT NOT NULL,          -- 正向风格词片段
    negative_fragment TEXT,                   -- 负向风格词片段
    -- 视觉参数
    dominant_colors VARCHAR(16)[],            -- 主色调hex值
    color_tone VARCHAR(64),
    lighting_style VARCHAR(64),
    lens_and_camera VARCHAR(128),
    composition_style VARCHAR(128),
    film_grain VARCHAR(64),                   -- 胶片颗粒
    aspect_ratio_hint VARCHAR(16),
    -- 模型参数建议
    parameter_hints JSONB DEFAULT '{}',       -- {"cfg_scale": 7, "sampler": "DPM++ 2M", "steps": 30, ...}
    recommended_loras JSONB DEFAULT '[]',     -- 推荐LoRA列表 [{name, weight, trigger_words, source_url}]
    -- 导演风格特有字段
    director_name VARCHAR(128),
    reference_films TEXT[],
    lut_reference VARCHAR(128),               -- 推荐LUT名称
    -- 示例
    example_image_url TEXT,
    example_prompt TEXT,
    -- 元数据
    tags TEXT[],
    is_preset BOOLEAN DEFAULT FALSE,
    usage_count INT DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_style_presets_owner ON style_presets(owner_id);
CREATE INDEX idx_style_presets_category ON style_presets(category);

-- 风格卡组合（支持叠加多个风格）
CREATE TABLE style_combinations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    owner_id UUID NOT NULL REFERENCES users(id),
    name VARCHAR(128) NOT NULL,
    style_ids UUID[] NOT NULL,                -- 引用的风格卡ID数组（有顺序，后者覆盖前者冲突项）
    merged_positive_fragment TEXT,            -- 合并后的正向片段
    merged_negative_fragment TEXT,            -- 合并后的负向片段
    merged_parameter_hints JSONB DEFAULT '{}',
    preview_image_url TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 场景库
CREATE TABLE scene_presets (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    owner_id UUID REFERENCES users(id),
    category VARCHAR(64) NOT NULL,            -- indoor/outdoor/fantasy/historic/urban/nature/...
    name VARCHAR(128) NOT NULL,
    description TEXT NOT NULL,                 -- 详细视觉描述
    prompt_fragment TEXT NOT NULL,
    lighting_default VARCHAR(128),
    time_of_day VARCHAR(32),
    weather VARCHAR(32),
    era VARCHAR(64),
    geography VARCHAR(64),
    reference_image_url TEXT,
    tags TEXT[],
    is_preset BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 道具库
CREATE TABLE prop_presets (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    owner_id UUID REFERENCES users(id),
    category VARCHAR(64),
    name VARCHAR(128) NOT NULL,
    description TEXT NOT NULL,
    prompt_fragment TEXT NOT NULL,
    era VARCHAR(64),
    material VARCHAR(64),
    size VARCHAR(32),
    reference_image_url TEXT,
    tags TEXT[],
    is_preset BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 品牌视觉规范包（企业用户）
CREATE TABLE brand_kits (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id UUID NOT NULL REFERENCES organizations(id),
    name VARCHAR(128) NOT NULL,
    brand_colors VARCHAR(16)[],               -- 品牌色hex
    logo_url TEXT,
    font_preferences JSONB,
    visual_tone VARCHAR(128),                 -- 品牌视觉调性（高端/亲民/科技/温暖…）
    forbidden_elements TEXT[],                -- 禁止出现的元素
    required_disclaimers TEXT[],              -- 必须加的免责声明/标识
    style_preset_ids UUID[],                  -- 关联的风格卡（强制使用）
    character_ids UUID[],                     -- 关联的品牌代言人/IP角色
    custom_prompt_prefix TEXT,                -- 自定义提示词前缀
    custom_prompt_suffix TEXT,                -- 自定义提示词后缀
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
```

### Step 3：预置资产库建设（必须亲手构建初版）

这是平台的"开箱即用"价值——用户注册进来就能用现成的角色、风格、场景。你（Agent）必须创建以下预置数据的JSON seed文件，存放在 `services/agent/src/knowledge/presets/`，配合`scripts/seed-db.sh`入库。

#### 3.1 预置角色卡（至少50个）

文件：`character_presets.json`

按以下分类至少各创建5-10个角色，每个角色有完整字段（face/hair/body/clothing/distinctive features/personality）：

- **年轻都市女性**（10个）：不同风格（职场干练/甜美可爱/酷飒飒/温柔知性/运动活力/时尚潮流/文艺清新/性感御姐/邻家女孩/学院风）
- **年轻都市男性**（10个）：不同风格（商务精英/阳光运动/文艺青年/潮流街头/程序员格子衫/成熟大叔/学院男/酷盖嘻哈/居家暖男/时尚男模）
- **中年/中老年**（各3个）：儒雅商务/家庭主妇/退休老人/专业人士（医生/老师/教授）
- **特殊类型**（10个）：古装古风/二次元动漫/赛博朋克/科幻未来/乡村田园/欧美/日韩/儿童/婴儿/拟人化动物角色
- **职业类型**（若干）：厨师/运动员/消防员/警察/医生/艺术家/音乐家/农民/外卖小哥/快递员

每个角色的prompt_fragment必须是**可直接拼接进提示词的专业描述**，例如：
```
"A 25-year-old East Asian woman, oval face with soft jawline, warm brown almond-shaped eyes with subtle double eyelids, small straight nose, natural pink lips with slight gloss, long wavy black hair reaching mid-back with side-swept bangs, fair skin with light peach blush, mole under left eye, wearing a cream-colored silk blouse with puffed sleeves, delicate gold necklace, warm and approachable expression, gentle smile"
```

#### 3.2 预置风格卡（至少100个）

文件：`style_presets.json`

必须覆盖：

**A. 基础视觉风格（25个）**：
- 写实类：写实照片、电影写实、杂志大片、广告级产品图、街拍纪实、自然光人像、影棚人像
- 艺术类：水彩画、油画、丙烯画、素描、工笔画、水墨画、浮世绘、像素艺术、矢量插画
- 二次元：日系动漫、赛璐璐、新海诚风格、吉卜力风格、国漫风、美式漫画、Pixar 3D、Disney 3D
- 设计类：3D渲染（C4D/Blender）、等距视角、Low Poly、黏土风、拼贴艺术、超现实主义

**B. 光影风格（20个）**：
自然光、黄金小时、蓝色时刻、阴天柔光、硬光、伦勃朗光、蝴蝶光、分割光、轮廓光/背光、顶光、底光、霓虹灯光、烛光/火光、窗户光、体积光/丁达尔效应、柔光箱影棚光、环形光、冷调月光、舞台追光、混合光

**C. 色调/调色风格（20个）**：
暖色调、冷色调、高饱和、低饱和莫兰迪、青橙色调(Teal & Orange)、复古胶片(Kodak 2383/Fuji C200)、黑白高对比、黑白低对比、褪色复古、日系清新、港风复古、赛博朋克霓虹、VHS复古录像带、暮光紫、马卡龙色、单色调、漂白旁路(Bleach Bypass)、奶油肌色调、青灰色调、糖果色

**D. 镜头/焦距/景深（15个）**：
广角镜头(24mm)、标准镜头(50mm)、长焦压缩(85-200mm)、微距镜头、鱼眼镜头、变形宽银幕(anamorphic)、浅景深f/1.4、深景深f/16、手持抖动、稳定器平滑、航拍俯视、GoPro运动、Drone飞行、IMAX 70mm镜头、Security Cam低画质

**E. 知名导演/摄影风格（20个）**：
- 电影：诺兰(黑暗骑士/奥本海默)、维伦纽夫(银翼杀手2049/沙丘)、王家卫(花样年华/重庆森林)、韦斯·安德森(布达佩斯大饭店)、诺娅·鲍姆巴赫(婚姻故事)、宫崎骏(千与千寻)、新海诚(你的名字)、奉俊昊(寄生虫)、大卫·芬奇(搏击俱乐部)、张艺谋(英雄)、侯孝贤(刺客聂隐娘)
- 摄影：Annie Leibovitz、Steve McCurry、Ansel Adams
- 剧集/广告：Netflix剧集感、Apple产品大片感、Nike运动广告感、美食纪录片(Chef's Table)感、旅行博主Vlog感

**F. 时代风格（10个）**：
80年代复古、90年代港风、2000年代Y2K、1920s爵士时代、1950s美式复古、1960s太空时代、1970s嬉皮、维多利亚时代、中国古代唐风、中国古代宋风

每个风格卡必须有：
- 具体的positive_fragment（可直接拼进prompt，50-150字，包含专业术语）
- negative_fragment（对应的负向词）
- 推荐参数（采样器/CFG/步数，针对主流模型给出建议）
- 适用场景说明
- 至少3个相关的关键词标签

例（王家卫风格片段）：
```
"Wong Kar-wai cinematic style, Christopher Doyle cinematography, step-printing motion blur, neon-lit Hong Kong streets at night, rain-slicked reflective surfaces, saturated red and green color palette, shallow depth of field, anamorphic lens flares, melancholic romantic atmosphere, intimate close-ups, cigarette smoke, cheongsam fabric texture, nostalgic 1960s period, grainy 35mm film stock, emotional longing, light refracting through rain drops"
```

#### 3.3 预置场景（至少100个）
文件：`scene_presets.json`，分类：室内家居(15)、商业空间(15)、户外自然(20)、城市街景(15)、餐饮美食(10)、虚构/奇幻(15)、历史/古风(10)

#### 3.4 预置道具（至少80个）
文件：`prop_presets.json`，分类：电子产品(10)、家居用品(10)、服装配饰(10)、食物饮品(15)、交通工具(10)、自然植物(10)、武器魔法(10)、办公文具(5)

所有预置资产必须由你基于专业知识认真填写描述词（不是随便写几个词），确保：
- prompt_fragment可以直接用于生图/生视频
- 描述词符合主流模型（MJ/SD/Flux/Kling/Runway）的识别习惯
- 不同风格/场景/角色之间没有重复冗余

### Step 4：角色创建Agent实现

在 `services/agent/src/agents/character/` 下：

```
agents/character/
├── __init__.py
├── character_designer.py     # 角色创建/补全Agent
├── image_analyzer.py         # 参考图分析Agent（多模态）
└── prompts/
    ├── character_designer.md
    └── image_analyzer.md
```

**角色创建支持三种方式**：

#### 4.1 文字描述创建
用户填写表单（姓名、性别、年龄段、简单描述如"温柔知性的职场女性"），Agent自动补全所有视觉细节：
- 面部特征（脸型、眼睛、鼻子、嘴唇、肤色、细节）
- 发型发色
- 体型
- 默认服装
- 标志性特征
- 推荐FaceID/IP-Adapter参数
- 生成完整的prompt_fragment
- 生成跨镜头seed建议

Agent Prompt核心指令：
```
你是角色视觉设计师，根据用户的简单描述，补全一个适合AI生图/生视频的角色完整描述。

规则：
1. 描述必须具体、可视化，禁止抽象形容词
2. 所有特征互相协调（年龄-服装-气质一致）
3. 生成的prompt_fragment必须可直接拼接到Midjourney/SD/Flux/Kling等模型的prompt中使用
4. 同时给出负面词（避免变形/失真）
5. 给出合理的FaceID权重建议（0.6-0.9范围）
6. 如果用户描述模糊，给出2-3个变体方案让用户选
```

#### 4.2 参考图创建
用户上传1-3张参考照片（正面/侧面），多模态Agent分析图片提取：
- 面部特征详细描述（脸型、五官、肤色、年龄感）
- 发型发色
- 体型（能看到的话）
- 穿着（当前照片的服装，但建议默认服装）
- 建议FaceID策略（用哪张作为参考、权重多少）

**关键技术**：
- 前端用 `react-image-crop` 允许用户裁剪面部区域
- 图片上传到MinIO后，Agent调用GPT-4o/Gemini多模态分析
- 如果用户上传多张，自动选择最清晰正面照作为主参考
- 同时生成纯文字描述版（防止完全依赖FaceID）

#### 4.3 角色库选择
用户从预置角色库浏览选择，可"基于此角色微调"（修改发型/年龄/服装等）生成新角色。

### Step 5：风格管理Agent实现

在 `services/agent/src/agents/style/` 下：

```
agents/style/
├── __init__.py
├── style_director.py         # 风格选择/组合/创建Agent
├── style_image_analyzer.py   # 参考图风格分析Agent
└── prompts/
    ├── style_director.md
    └── style_image_analyzer.md
```

**功能**：
1. **风格选择向导**：Agent通过2-3个简单问题帮用户找到合适风格（"想要写实还是艺术化？"/"明亮清新还是暗调电影感？"/"现代还是复古？"）
2. **风格组合**：用户选多个风格（如"电影感+赛博朋克+青橙色调"），Agent自动处理冲突、合并positive/negative片段
3. **参考图风格分析**：上传参考图片/电影截图，Agent分析识别视觉风格，匹配到预置风格卡，或创建自定义风格
4. **品牌风格包创建**：企业用户上传品牌VI手册/参考产品图，自动提取品牌色、调性，生成品牌风格包

**风格组合逻辑**：
- 多个风格positive_fragment拼接时，避免重复词
- 冲突项（如"高饱和"和"低饱和"同时出现）提示用户选择
- 负面词合并去重
- 参数取更保守/更安全的值（如steps取各风格的最大值，CFG取中位）
- 组合后的风格保存为style_combination供复用

### Step 6：场景/道具检索Agent

- 提供自然语言搜索场景/道具："一个雨夜的赛博朋克城市街道" → 向量检索匹配最相似场景
- 如果预置库没有匹配，Agent可以即时生成一个自定义场景描述（作为用户自定义资产保存）
- 场景/道具选择后，自动将prompt_fragment注入到分镜提示词中

### Step 7：API实现

| 方法 | 路径 | 功能 |
|:---|:---|:---|
| GET | `/api/v1/characters` | 我的角色列表（含预置公共角色） |
| POST | `/api/v1/characters` | 创建角色（文字描述，异步返回补全结果） |
| POST | `/api/v1/characters/from-image` | 从参考图创建角色（上传图片+分析） |
| GET | `/api/v1/characters/:id` | 角色详情 |
| PUT | `/api/v1/characters/:id` | 修改角色 |
| DELETE | `/api/v1/characters/:id` | 删除角色 |
| POST | `/api/v1/characters/:id/ref-images` | 上传参考图片 |
| DELETE | `/api/v1/characters/:id/ref-images/:imgId` | 删除参考图 |
| POST | `/api/v1/characters/:id/variant` | 基于该角色创建变体（修改部分属性） |
| GET | `/api/v1/styles` | 风格卡列表（可按分类/标签筛选） |
| POST | `/api/v1/styles` | 创建自定义风格 |
| POST | `/api/v1/styles/from-image` | 从参考图分析风格 |
| POST | `/api/v1/styles/combine` | 组合多个风格（返回合并结果） |
| GET | `/api/v1/style-combinations` | 我的风格组合 |
| POST | `/api/v1/style-combinations` | 保存风格组合 |
| GET | `/api/v1/scenes` | 场景库搜索 |
| GET | `/api/v1/props` | 道具库搜索 |
| CRUD | `/api/v1/brand-kits` | 品牌包管理 |

### Step 8：前端实现

在 `apps/web/src/app/` 下：

```
app/assets/
├── characters/
│   ├── page.tsx                    # 角色库总览（我的角色+预置角色）
│   ├── new/page.tsx                # 创建新角色（表单/上传参考图）
│   ├── [id]/page.tsx               # 角色详情/编辑
│   └── components/
│       ├── character-card.tsx              # 角色卡片（网格展示参考图+名字）
│       ├── character-form.tsx              # 角色创建/编辑表单
│       ├── image-uploader.tsx              # 图片上传裁剪组件（react-dropzone + react-image-crop）
│       ├── face-ref-gallery.tsx            # 参考图画廊
│       ├── character-prompt-preview.tsx    # prompt_fragment实时预览
│       └── character-fields-ai-fill.tsx    # 一键AI补全按钮
├── styles/
│   ├── page.tsx                    # 风格库（分类浏览：视觉/光影/色调/镜头/导演）
│   ├── new/page.tsx
│   ├── [id]/page.tsx
│   └── components/
│       ├── style-card.tsx
│       ├── style-gallery.tsx               # 瀑布流展示，带预览图
│       ├── style-filter.tsx                # 分类筛选侧边栏
│       ├── style-composer.tsx              # 风格组合器（多选标签，实时预览合并后的prompt）
│       ├── color-palette-picker.tsx        # 色板选择器
│       ├── lora-recommender.tsx            # LoRA推荐列表
│       └── style-from-image.tsx            # 上传图片分析风格
├── scenes/
│   └── page.tsx + components      # 场景浏览/搜索
└── brand-kits/
    └── page.tsx + components      # 品牌包管理
```

**UI/UX核心要求**：
- 角色创建要有一个"AI补全"按钮：用户输入3-5个关键词，点一下Agent自动填满所有字段（可以再微调）
- 参考图上传支持拖拽+粘贴+点击，上传后自动开始AI分析
- 风格选择器要有**视觉预览**：每张风格卡配一张代表图（预置），用户一眼看到效果
- 风格组合器类似"标签多选"，已选风格显示为chip标签，实时显示合并后的prompt预览
- 所有prompt_fragment有"一键复制"按钮，方便高级用户直接用

### Step 9：与脚本/分镜的联动

- 创建项目时可选择默认角色和风格
- 脚本生成时，如果有选定角色/风格，Agent自动把角色/风格信息融入creative_brief
- 分镜生成时，自动注入角色prompt_fragment到subject_description、风格positive_fragment到color_tone/lighting
- 角色一致性策略自动应用：seed_base建议、FaceID权重、首尾帧建议都写入consistency_hints
- 产出ScriptPackage时携带完整的Character/Style信息给提示词引擎

## 验收标准

- [ ] 数据库表创建完成，migration可up/down
- [ ] 预置角色≥50个、风格卡≥100个、场景≥100个、道具≥80个，每个都有完整可用的prompt_fragment
- [ ] 文字创建角色：输入"温柔知性的职场女性"，Agent补全10+个维度的视觉描述，生成可用prompt_fragment
- [ ] 参考图创建角色：上传人像照片，Agent分析出面部特征描述（人工验证准确性≥80%）
- [ ] 风格组合：选3个风格（如"电影感+赛博朋克+青橙色调"），能合并生成无冲突的positive/negative片段
- [ ] 参考图风格分析：上传电影截图，能正确识别导演风格/色调/光影类型
- [ ] 角色卡CRUD完整，参考图可上传/删除/设主图
- [ ] 风格卡浏览/筛选/搜索/创建/组合可用
- [ ] 场景/道具语义搜索可用（用向量检索）
- [ ] 品牌包CRUD，创建后能在项目中选择并自动注入前后缀
- [ ] 前端页面美观流畅，角色/风格/场景管理页完整
- [ ] 与脚本/分镜Agent联动正常：选择角色后分镜自动包含角色描述
- [ ] `docs/research/04-character-style.md` 调研记录完整
- [ ] `make lint && make test` 通过
